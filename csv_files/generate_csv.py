"""Generate test CSV data for the transaction system."""

import csv
import random
from datetime import datetime, timedelta
from decimal import Decimal
from uuid import uuid4


def generate_test_csv(filename: str = "test_transactions.csv", num_rows: int = 100) -> None:
    """Generate a CSV file with test transaction data."""
    
    # Sample customers and products
    customers = [uuid4() for _ in range(10)]
    products = [uuid4() for _ in range(20)]
    currencies = ["PLN", "EUR", "USD"]
    
    # Start date
    start_date = datetime(2024, 1, 1)
    
    with open(filename, "w", newline="", encoding="utf-8") as csvfile:
        fieldnames = [
            "transaction_id",
            "timestamp",
            "amount",
            "currency",
            "customer_id",
            "product_id",
            "quantity",
        ]
        
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        
        for i in range(num_rows):
            # Generate transaction data
            transaction_date = start_date + timedelta(
                days=random.randint(0, 90),
                hours=random.randint(0, 23),
                minutes=random.randint(0, 59),
            )
            
            amount = Decimal(random.uniform(10, 500)).quantize(Decimal("0.01"))
            
            row = {
                "transaction_id": uuid4(),
                "timestamp": transaction_date.isoformat() + "Z",
                "amount": str(amount),
                "currency": random.choice(currencies),
                "customer_id": random.choice(customers),
                "product_id": random.choice(products),
                "quantity": random.randint(1, 10),
            }
            
            writer.writerow(row)
    
    print(f"Generated {num_rows} transactions in {filename}")
    print(f"Customers: {len(customers)}")
    print(f"Products: {len(products)}")


if __name__ == "__main__":
    generate_test_csv("csv/large_test_data.csv", 1000)
