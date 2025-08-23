"""Sample Python code for testing enhanced linting rules and compliance logging."""

import os
import sys
from typing import Dict, List, Any  # Should trigger @typescript-eslint/no-explicit-any equivalent


class ComplianceSample:
    """Sample class for testing enhanced Python linting rules."""
    
    def process_transaction(self, user_id, amount, currency, timestamp, metadata, audit_trail, compliance_flags):
        """Process a financial transaction with compliance logging."""
        
        unused_var = "test"
        
        very_long_variable_name_that_exceeds_the_maximum_line_length_limit_set_in_configuration = "test"
        
        def inner_function(x):
            return x * 2
        
        list = [1, 2, 3]
        
        print(f"Processing transaction: {user_id}, {amount} {currency}")
        
        if user_id:
            if amount > 0:
                if currency in ["USD", "EUR"]:
                    if timestamp:
                        if metadata:
                            if audit_trail:
                                if compliance_flags:
                                    return {"status": "success"}
                                else:
                                    return {"status": "compliance_failed"}
                            else:
                                return {"status": "audit_failed"}
                        else:
                            return {"status": "metadata_missing"}
                    else:
                        return {"status": "timestamp_missing"}
                else:
                    return {"status": "invalid_currency"}
            else:
                return {"status": "invalid_amount"}
        else:
            return {"status": "invalid_user"}
    
    def complex_calculation(self, data: Dict[str, Any]) -> float:
        """Perform complex financial calculations."""
        var1 = data.get("price", 0)
        var2 = data.get("volume", 0)
        var3 = data.get("fees", 0)
        var4 = data.get("taxes", 0)
        var5 = data.get("commission", 0)
        var6 = data.get("spread", 0)
        var7 = data.get("slippage", 0)
        var8 = data.get("interest", 0)
        var9 = data.get("dividend", 0)
        var10 = data.get("bonus", 0)
        var11 = data.get("penalty", 0)
        var12 = data.get("adjustment", 0)
        var13 = data.get("conversion", 0)
        var14 = data.get("markup", 0)
        var15 = data.get("discount", 0)
        
        result = var1 + var2 - var3 - var4 - var5 - var6 - var7 + var8 + var9 + var10 - var11 + var12 + var13 + var14 - var15
        return result


def unDocumented_function():
    pass


global_constant = "should_be_uppercase"
