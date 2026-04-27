# fx/services/payment.py
# This module handles user upgrades via crypto payments.
# 
# IMPORTANT: Blockchain detection is handled by Billing service.
# This module ONLY:
# 1. Creates payment requests in Billing
# 2. Polls Billing for payment status
# 3. Notifies users based on status
# 4. Never touches blockchain directly!

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum
import uuid

import aiohttp
from sqlalchemy import Column, String, Integer, DateTime, Enum as SQLEnum
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()
logger = logging.getLogger(__name__)

# Domain Models
class PaymentStatus(str, Enum):
    """Payment status - mirrors Billing service states"""
    PENDING = "pending"        # Created, waiting for user to send crypto
    CONFIRMED = "confirmed"    # TX detected on blockchain, confirming
    ACTIVATED = "activated"    # Enough confirmations, subscription upgraded
    EXPIRED = "expired"        # Crypto window (2h) elapsed with no TX
    FAILED = "failed"          # Payment failed (wrong amount, etc)


class PaymentMethod(str, Enum):
    """Crypto payment methods"""
    USDT_ERC20 = "usdt_erc20"  # USDT on Ethereum
    BTC = "btc"                # Bitcoin


@dataclass
class CryptoCheckoutResponse:
    """Response from POST /checkout/crypto"""
    payment_id: str
    address: str
    amount: str          # e.g., "29.900347"
    currency: str        # "USDT" or "BTC"
    expires_at: str      # ISO 8601 datetime
    expires_minutes: int


@dataclass
class PaymentStatusResponse:
    """Response from GET /payments/:id/status"""
    payment_id: str
    status: PaymentStatus
    confirmations: int = 0
    tx_hash: Optional[str] = None
    confirmed_at: Optional[str] = None
    expires_at: Optional[str] = None


class PaymentRequest(Base):
    """Local record of payment request (for tracking in Bot DB)"""
    __tablename__ = "payment_requests"
    
    id = Column(String, primary_key=True)               # UUID
    payment_id = Column(String, unique=True, index=True) # Billing's payment_id
    user_id = Column(String, index=True)                # Telegram user_id
    plan_id = Column(String)                            # 'pro', 'basic', etc
    amount_usd = Column(Integer)                        # In cents (e.g., 2990 = $29.90)
    crypto_amount = Column(String)                      # "29.900347"
    crypto_currency = Column(String)                    # "USDT" or "BTC"
    address = Column(String)                            # Wallet address
    status = Column(SQLEnum(PaymentStatus))             # Current status
    expires_at = Column(DateTime)                       # When this request expires
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# Billing Service Client
class BillingClient:
    """HTTP client for Billing service - handles all payment operations"""
    
    def __init__(self, billing_url: str, api_key: str, timeout: int = 10):
        """
        Initialize Billing client.
        
        Args:
            billing_url: Base URL of Billing service (e.g., https://billing.tonpo.io)
            api_key: API key for authentication (X-API-Key header)
            timeout: Request timeout in seconds
        """
        self.billing_url = billing_url.rstrip('/')
        self.api_key = api_key
        self.timeout = aiohttp.ClientTimeout(total=timeout)
    
    async def _request(
        self,
        method: str,
        endpoint: str,
        json_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Make authenticated request to Billing service"""
        url = f"{self.billing_url}{endpoint}"
        headers = {"X-API-Key": self.api_key}
        
        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            async with session.request(method, url, json=json_data, headers=headers) as resp:
                if resp.status != 200:
                    error_body = await resp.text()
                    raise Exception(f"Billing API error {resp.status}: {error_body}")
                
                return await resp.json()
    
    async def create_crypto_payment(
        self,
        user_id: str,
        plan_id: str,
        method: PaymentMethod
    ) -> CryptoCheckoutResponse:
        """
        POST /checkout/crypto
        
        Create a crypto payment request.
        Billing will generate unique amount and return payment details.
        
        Args:
            user_id: Telegram user ID
            plan_id: Plan to upgrade to ('pro', 'basic', etc)
            method: PaymentMethod.USDT_ERC20 or PaymentMethod.BTC
        
        Returns:
            CryptoCheckoutResponse with payment details
        """
        logger.info(f"Creating crypto checkout: user={user_id}, plan={plan_id}, method={method}")
        
        response = await self._request(
            "POST",
            "/checkout/crypto",
            {
                "user_id": user_id,
                "plan_id": plan_id,
                "method": method.value
            }
        )
        
        return CryptoCheckoutResponse(
            payment_id=response["payment_id"],
            address=response["address"],
            amount=response["amount"],
            currency=response["currency"],
            expires_at=response["expires_at"],
            expires_minutes=response["expires_minutes"]
        )
    
    async def get_payment_status(self, payment_id: str) -> PaymentStatusResponse:
        """
        GET /payments/:id/status
        
        Poll current payment status from Billing.
        Billing updates this automatically when blockchain confirms.
        
        Args:
            payment_id: Payment ID from Billing
        
        Returns:
            PaymentStatusResponse with current status
        """
        response = await self._request("GET", f"/payments/{payment_id}/status")
        
        return PaymentStatusResponse(
            payment_id=response["payment_id"],
            status=PaymentStatus(response["status"]),
            confirmations=response.get("confirmations", 0),
            tx_hash=response.get("tx_hash"),
            confirmed_at=response.get("confirmed_at"),
            expires_at=response.get("expires_at")
        )

# Payment Manager - Handles User Upgrade Flow
class PaymentManager:
    """Orchestrates crypto payment flow - pure routing + polling"""
    
    def __init__(self, billing_client: BillingClient, db_session):
        """
        Args:
            billing_client: BillingClient instance
            db_session: SQLAlchemy session for local DB
        """
        self.billing = billing_client
        self.db = db_session
    
    async def initiate_upgrade(
        self,
        user_id: str,
        plan_id: str,
        method: PaymentMethod = PaymentMethod.USDT_ERC20
    ) -> CryptoCheckoutResponse:
        """
        Step 1: User clicks "Upgrade to Pro"
        
        Create crypto payment request in Billing and return payment details.
        
        Args:
            user_id: Telegram user ID
            plan_id: Target plan ('pro', 'basic', etc)
            method: Payment method (USDT or BTC)
        
        Returns:
            Payment details to show to user (address, amount, expires_at)
        """
        logger.info(f"Initiating upgrade: user={user_id} → {plan_id}")
        
        # Call Billing to create payment
        checkout = await self.billing.create_crypto_payment(user_id, plan_id, method)
        
        # Store in local DB for tracking
        payment_record = PaymentRequest(
            id=str(uuid.uuid4()),
            payment_id=checkout.payment_id,      # Billing's ID
            user_id=user_id,
            plan_id=plan_id,
            crypto_amount=checkout.amount,
            crypto_currency=checkout.currency,
            address=checkout.address,
            status=PaymentStatus.PENDING,
            expires_at=datetime.fromisoformat(checkout.expires_at.replace('Z', '+00:00'))
        )
        self.db.add(payment_record)
        self.db.commit()
        
        logger.info(f"Payment created: {checkout.payment_id}, expires in {checkout.expires_minutes}m")
        
        return checkout
    
    async def monitor_payment(
        self,
        payment_id: str,
        user_id: str,
        notification_callback
    ) -> bool:
        """
        Step 2: Monitor payment status (polling)
        
        Poll Billing's /payments/:id/status endpoint until payment completes.
        Billing's background job handles blockchain detection automatically.
        
        This function just asks Billing: "Is it done yet?"
        
        Args:
            payment_id: Payment ID from Billing
            user_id: Telegram user ID (for logging)
            notification_callback: async function(status, confirmations, message)
        
        Returns:
            True if payment activated, False if expired/failed
        """
        logger.info(f"Monitoring payment {payment_id} for user {user_id}")
        
        max_polls = 120  # 2 hours (120 * 60 sec = 2 hours, polling every 60 sec)
        poll_count = 0
        last_confirmations = 0
        
        while poll_count < max_polls:
            try:
                # Ask Billing: What's the status?
                status = await self.billing.get_payment_status(payment_id)
                
                # Update local DB
                self._update_payment_status(payment_id, status.status)

                # Handle Status Changes
                if status.status == PaymentStatus.PENDING:
                    # Still waiting for user to send crypto
                    message = "⏳ Waiting for payment..."
                    await notification_callback(
                        status=status.status,
                        confirmations=0,
                        message=message
                    )
                
                elif status.status == PaymentStatus.CONFIRMED:
                    # Blockchain found the TX! Counting confirmations.
                    confirmations = status.confirmations or 0
                    
                    # Only notify on confirmation change
                    if confirmations != last_confirmations:
                        message = f"⏳ Payment detected! {confirmations}/12 confirmations"
                        await notification_callback(
                            status=status.status,
                            confirmations=confirmations,
                            message=message
                        )
                        last_confirmations = confirmations
                    
                    # Keep polling until 12 confirmations
                    await asyncio.sleep(60)  # Poll every 60 seconds
                    poll_count += 1
                    continue
                
                elif status.status == PaymentStatus.ACTIVATED:
                    # 🎉 Payment complete! Subscription upgraded!
                    message = "✅ Pro plan activated! You can now trade with full features."
                    await notification_callback(
                        status=status.status,
                        confirmations=status.confirmations or 12,
                        message=message
                    )
                    logger.info(f"Payment {payment_id} activated for user {user_id}")
                    return True
                
                elif status.status == PaymentStatus.EXPIRED:
                    # ❌ User didn't send crypto in time
                    message = "❌ Payment window expired (2 hours). Please try again."
                    await notification_callback(
                        status=status.status,
                        confirmations=0,
                        message=message
                    )
                    logger.warning(f"Payment {payment_id} expired for user {user_id}")
                    return False
                
                elif status.status == PaymentStatus.FAILED:
                    # ❌ Payment failed (wrong amount, etc)
                    message = "❌ Payment failed. Please contact support."
                    await notification_callback(
                        status=status.status,
                        confirmations=0,
                        message=message
                    )
                    logger.error(f"Payment {payment_id} failed for user {user_id}")
                    return False
                
                # Wait before next poll
                await asyncio.sleep(60)  # Poll every 60 seconds
                poll_count += 1
            
            except Exception as e:
                logger.error(f"Error monitoring payment {payment_id}: {e}")
                await notification_callback(
                    status=PaymentStatus.FAILED,
                    confirmations=0,
                    message=f"❌ Error checking payment status: {str(e)}"
                )
                await asyncio.sleep(60)
                poll_count += 1
        
        # Timeout
        logger.warning(f"Payment {payment_id} monitoring timeout for user {user_id}")
        return False
    
    def _update_payment_status(self, payment_id: str, status: PaymentStatus) -> None:
        """Update local payment record status"""
        payment = self.db.query(PaymentRequest)\
            .filter(PaymentRequest.payment_id == payment_id)\
            .first()
        
        if payment:
            payment.status = status
            payment.updated_at = datetime.utcnow()
            self.db.commit()

# Telegram Bot Integration
class CryptoPaymentHandler:
    """Handles /upgrade command and payment flow in Telegram Bot"""
    
    def __init__(self, payment_manager: PaymentManager, telegram_client):
        """
        Args:
            payment_manager: PaymentManager instance
            telegram_client: Telegram bot client for sending messages
        """
        self.payment = payment_manager
        self.telegram = telegram_client
    
    async def handle_upgrade_command(self, user_id: str, telegram_id: str, plan_id: str = "pro"):
        """
        User runs: /upgrade
        
        Orchestrate the entire upgrade flow:
        1. Create payment in Billing
        2. Show QR code + instructions
        3. Poll for completion
        4. Notify user
        """
        try:
            # Step 1: Initiate payment
            await self.telegram.send_message(
                telegram_id,
                "🔄 Setting up payment...",
                parse_mode="Markdown"
            )
            
            checkout = await self.payment.initiate_upgrade(
                user_id=user_id,
                plan_id=plan_id,
                method=PaymentMethod.USDT_ERC20
            )
            
            # Step 2: Show payment instructions
            message = (
                f"💳 **Upgrade to Pro - $29.90/month**\n\n"
                f"**Send exactly:**\n"
                f"`{checkout.amount} {checkout.currency}`\n\n"
                f"**To address:**\n"
                f"`{checkout.address}`\n\n"
                f"⏰ **Expires in:** {checkout.expires_minutes} minutes\n\n"
                f"✨ **Benefits:**\n"
                f"• 5 MT5 accounts (vs 1)\n"
                f"• 10 webhooks (vs 3)\n"
                f"• 500 API req/min (vs 100)\n\n"
                f"🔗 After you send, we'll detect it automatically!\n"
                f"Check back here for confirmation."
            )
            
            await self.telegram.send_message(
                telegram_id,
                message,
                parse_mode="Markdown"
            )
            
            # Step 3: Monitor payment (polling)
            async def notify(status: PaymentStatus, confirmations: int, message: str):
                """Callback when payment status changes"""
                await self.telegram.send_message(
                    telegram_id,
                    message,
                    parse_mode="Markdown"
                )
            
            success = await self.payment.monitor_payment(
                payment_id=checkout.payment_id,
                user_id=user_id,
                notification_callback=notify
            )
            
            # Step 4: Final message
            if success:
                await self.telegram.send_message(
                    telegram_id,
                    (
                        "🎉 **Welcome to Pro!**\n\n"
                        "You can now:\n"
                        "• Create 5 MT5 accounts\n"
                        "• Set 10 webhooks\n"
                        "• 500 API requests/min\n\n"
                        "Run /balance to see your account info."
                    ),
                    parse_mode="Markdown"
                )
            
        except Exception as e:
            logger.error(f"Error in upgrade command for {user_id}: {e}")
            await self.telegram.send_message(
                telegram_id,
                f"❌ Error: {str(e)}\n\nPlease try again or contact support.",
                parse_mode="Markdown"
            )
