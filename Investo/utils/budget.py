def is_token_budget_low(tokens_used, primary_budget, threshold_percent=10):
    """
    Returns True if the remaining token budget is less than or equal to the threshold percentage.
    """
    if primary_budget == 0:
        return True  # Avoid division by zero; treat as low budget.
    remaining_percent = 100 * (primary_budget - tokens_used) / primary_budget
    return remaining_percent <= threshold_percent