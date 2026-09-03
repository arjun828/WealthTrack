"""Portfolio calculation helpers.

Pure functions for turning raw holding data (quantity, purchase price,
current price) into invested amount, current value, profit/loss, return
percentage, and aggregated portfolio totals.

Owned by Agent 3. See TASKS.md for the interface contract — do not change
function names/signatures/return shapes without updating that file, since
Agent 4's backend imports this module directly.
"""

ROUND_DECIMALS = 2


def calculate_invested_amount(quantity: float, purchase_price: float) -> float:
    """Total amount originally invested: quantity * purchase_price."""
    return round(quantity * purchase_price, ROUND_DECIMALS)


def calculate_current_value(quantity: float, current_price: float) -> float:
    """Current market value of the holding: quantity * current_price."""
    return round(quantity * current_price, ROUND_DECIMALS)


def calculate_profit_loss(invested_amount: float, current_value: float) -> float:
    """Profit (positive) or loss (negative): current_value - invested_amount."""
    return round(current_value - invested_amount, ROUND_DECIMALS)


def calculate_return_percentage(invested_amount: float, profit_loss: float) -> float:
    """Return on investment as a percentage.

    Guards against division by zero: if invested_amount is 0, returns 0.0
    instead of raising.
    """
    if invested_amount == 0:
        return 0.0
    return round((profit_loss / invested_amount) * 100, ROUND_DECIMALS)


def calculate_portfolio_totals(holdings: list) -> dict:
    """Aggregate invested_amount / current_value / profit_loss across holdings.

    Each item in `holdings` is a dict that already has 'invested_amount',
    'current_value', and 'profit_loss' keys computed. total_return_pct is
    derived from the summed totals (not averaged per-holding).
    """
    total_invested = round(sum(h["invested_amount"] for h in holdings), ROUND_DECIMALS)
    total_current_value = round(sum(h["current_value"] for h in holdings), ROUND_DECIMALS)
    total_profit_loss = round(sum(h["profit_loss"] for h in holdings), ROUND_DECIMALS)
    total_return_pct = calculate_return_percentage(total_invested, total_profit_loss)

    return {
        "total_invested": total_invested,
        "total_current_value": total_current_value,
        "total_profit_loss": total_profit_loss,
        "total_return_pct": total_return_pct,
    }


if __name__ == "__main__":
    # --- Holding 1: 10 shares bought at $150, now worth $180 ---
    q1, pp1, cp1 = 10, 150.0, 180.0
    inv1 = calculate_invested_amount(q1, pp1)
    cur1 = calculate_current_value(q1, cp1)
    pl1 = calculate_profit_loss(inv1, cur1)
    ret1 = calculate_return_percentage(inv1, pl1)
    assert inv1 == 1500.0, inv1
    assert cur1 == 1800.0, cur1
    assert pl1 == 300.0, pl1
    assert ret1 == 20.0, ret1

    # --- Holding 2: 5 shares bought at $200, now worth $150 (a loss) ---
    q2, pp2, cp2 = 5, 200.0, 150.0
    inv2 = calculate_invested_amount(q2, pp2)
    cur2 = calculate_current_value(q2, cp2)
    pl2 = calculate_profit_loss(inv2, cur2)
    ret2 = calculate_return_percentage(inv2, pl2)
    assert inv2 == 1000.0, inv2
    assert cur2 == 750.0, cur2
    assert pl2 == -250.0, pl2
    assert ret2 == -25.0, ret2

    # --- Holding 3: 2.5 shares bought at $100.50, now worth $120.25 (fractional qty) ---
    q3, pp3, cp3 = 2.5, 100.50, 120.25
    inv3 = calculate_invested_amount(q3, pp3)
    cur3 = calculate_current_value(q3, cp3)
    pl3 = calculate_profit_loss(inv3, cur3)
    ret3 = calculate_return_percentage(inv3, pl3)
    assert inv3 == 251.25, inv3
    assert cur3 == round(q3 * cp3, 2) == 300.62, cur3  # quantity*current_price, rounded to cents
    assert pl3 == round(cur3 - inv3, 2), pl3
    assert round(ret3, 2) == round((pl3 / inv3) * 100, 2), ret3

    # --- Zero-division guard ---
    assert calculate_return_percentage(0, 0) == 0.0
    assert calculate_return_percentage(0, 500) == 0.0

    # --- Portfolio totals across all three holdings, verified by hand ---
    holdings = [
        {"invested_amount": inv1, "current_value": cur1, "profit_loss": pl1},
        {"invested_amount": inv2, "current_value": cur2, "profit_loss": pl2},
        {"invested_amount": inv3, "current_value": cur3, "profit_loss": pl3},
    ]
    totals = calculate_portfolio_totals(holdings)

    expected_total_invested = round(inv1 + inv2 + inv3, 2)
    expected_total_current = round(cur1 + cur2 + cur3, 2)
    expected_total_pl = round(pl1 + pl2 + pl3, 2)
    expected_total_ret = round((expected_total_pl / expected_total_invested) * 100, 2)

    assert totals["total_invested"] == expected_total_invested, totals
    assert totals["total_current_value"] == expected_total_current, totals
    assert totals["total_profit_loss"] == expected_total_pl, totals
    assert totals["total_return_pct"] == expected_total_ret, totals

    # Manual hand-check against literal numbers: 1500+1000+251.25=2751.25,
    # 1800+750+300.62(5)=2850.625->2850.62(rounded), P&L 300-250+49.375=99.38(ish)
    assert totals["total_invested"] == 2751.25
    assert totals["total_profit_loss"] == round(300.0 - 250.0 + pl3, 2)

    print("All calculations.py self-tests passed.")
    print("Holding 1:", inv1, cur1, pl1, ret1)
    print("Holding 2:", inv2, cur2, pl2, ret2)
    print("Holding 3:", inv3, cur3, pl3, ret3)
    print("Portfolio totals:", totals)
