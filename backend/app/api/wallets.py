"""
Wallet Operations API
=====================

Manage user wallets, deposits, withdrawals, and transaction history.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from typing import List
from decimal import Decimal

from app.database import get_db
from app.schemas import WalletResponse, WalletDeposit, WalletWithdraw, TransactionResponse
from app.auth import get_current_user_id

router = APIRouter()


@router.get("/wallet", response_model=WalletResponse)
async def get_wallet(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Get current user's wallet information.
    """
    result = await db.execute(
        text("""
            SELECT 
                wallet_id, user_id, balance_usd, reserved_usd,
                lifetime_deposits, lifetime_fees, created_at
            FROM user_wallets
            WHERE user_id = :user_id
        """),
        {"user_id": user_id}
    )
    
    wallet = result.first()
    if not wallet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Wallet not found"
        )
    
    return WalletResponse(
        wallet_id=str(wallet.wallet_id),
        user_id=str(wallet.user_id),
        balance_usd=wallet.balance_usd,
        reserved_usd=wallet.reserved_usd,
        lifetime_deposits=wallet.lifetime_deposits,
        lifetime_fees=wallet.lifetime_fees,
        created_at=wallet.created_at
    )


@router.post("/wallet/deposit", response_model=TransactionResponse)
async def deposit_to_wallet(
    deposit_data: WalletDeposit,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Deposit funds to wallet.
    
    In production, this would integrate with payment gateway.
    For now, it directly credits the wallet.
    """
    # Call credit_wallet function
    result = await db.execute(
        text("""
            SELECT credit_wallet(
                :user_id::uuid,
                :amount::decimal,
                'DEPOSIT'::ledger_entry_type,
                :description
            ) as ledger_id
        """),
        {
            "user_id": user_id,
            "amount": str(deposit_data.amount_usd),
            "description": deposit_data.description
        }
    )
    
    ledger_id = result.scalar()
    await db.commit()
    
    # Fetch transaction details
    result = await db.execute(
        text("""
            SELECT 
                ledger_id, entry_type, amount_usd,
                balance_before, balance_after, description, created_at
            FROM billing_ledger
            WHERE ledger_id = :ledger_id
        """),
        {"ledger_id": str(ledger_id)}
    )
    
    transaction = result.first()
    
    return TransactionResponse(
        ledger_id=str(transaction.ledger_id),
        entry_type=transaction.entry_type,
        amount_usd=transaction.amount_usd,
        balance_before=transaction.balance_before,
        balance_after=transaction.balance_after,
        description=transaction.description,
        created_at=transaction.created_at
    )


@router.post("/wallet/withdraw", response_model=TransactionResponse)
async def withdraw_from_wallet(
    withdraw_data: WalletWithdraw,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Withdraw funds from wallet.
    
    In production, this would integrate with payment gateway.
    """
    try:
        # Call debit_wallet function
        result = await db.execute(
            text("""
                SELECT debit_wallet(
                    :user_id::uuid,
                    :amount::decimal,
                    'WITHDRAWAL'::ledger_entry_type,
                    :description,
                    NULL
                ) as ledger_id
            """),
            {
                "user_id": user_id,
                "amount": str(withdraw_data.amount_usd),
                "description": withdraw_data.description
            }
        )
        
        ledger_id = result.scalar()
        await db.commit()
        
    except Exception as e:
        await db.rollback()
        if "Insufficient balance" in str(e):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Insufficient balance"
            )
        raise
    
    # Fetch transaction details
    result = await db.execute(
        text("""
            SELECT 
                ledger_id, entry_type, amount_usd,
                balance_before, balance_after, description, created_at
            FROM billing_ledger
            WHERE ledger_id = :ledger_id
        """),
        {"ledger_id": str(ledger_id)}
    )
    
    transaction = result.first()
    
    return TransactionResponse(
        ledger_id=str(transaction.ledger_id),
        entry_type=transaction.entry_type,
        amount_usd=transaction.amount_usd,
        balance_before=transaction.balance_before,
        balance_after=transaction.balance_after,
        description=transaction.description,
        created_at=transaction.created_at
    )


@router.get("/wallet/transactions", response_model=List[TransactionResponse])
async def get_transactions(
    limit: int = 50,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Get wallet transaction history.
    """
    result = await db.execute(
        text("""
            SELECT 
                ledger_id, entry_type, amount_usd,
                balance_before, balance_after, description, created_at
            FROM billing_ledger
            WHERE user_id = :user_id
            ORDER BY created_at DESC
            LIMIT :limit
        """),
        {"user_id": user_id, "limit": limit}
    )
    
    transactions = []
    for row in result:
        transactions.append(TransactionResponse(
            ledger_id=str(row.ledger_id),
            entry_type=row.entry_type,
            amount_usd=row.amount_usd,
            balance_before=row.balance_before,
            balance_after=row.balance_after,
            description=row.description,
            created_at=row.created_at
        ))
    
    return transactions
