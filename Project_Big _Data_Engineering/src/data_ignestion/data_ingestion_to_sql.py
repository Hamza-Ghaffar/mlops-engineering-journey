import sys
import pathlib
import pandas as pd
import mysql.connector
from mysql.connector import Error

# Ensure src/ is on sys.path so we can import db_connection when running from project root
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
# Import the database connection from db_connection.py
from db_connection import connection, hostname, database, port, username, password

# Read the CSV file from the provided URL into a DataFrame
olist_order_payments_dataset_df = pd.read_csv('https://raw.githubusercontent.com/Hamza-Ghaffar/mlops-engineering-journey/refs/heads/develop/Project_Big%20_Data_Engineering/datasets/olist_order_payments_dataset.csv')

print(olist_order_payments_dataset_df.head())
print(olist_order_payments_dataset_df.info())

# Define the CSV file path (URL) and the table name for insertion
csv_file_path = 'https://raw.githubusercontent.com/Hamza-Ghaffar/mlops-engineering-journey/refs/heads/develop/Project_Big%20_Data_Engineering/datasets/olist_order_payments_dataset.csv'

print(f"CSV file path: {csv_file_path}")

# Table name where the data will be uploaded
table_name = "olist_order_payments"
print(f"Table name: {table_name}")



# The connection is established in db_connection.py, so we can directly use it here for data insertion.

try:
    # Step 1: Establish a connection to MySQL server
    connection = mysql.connector.connect(
        host=hostname,
        database=database,
        user=username,
        password=password,
        port=port
    )
    if connection.is_connected():
        print("Connected to MySQL Server successfully!")

        # Step 2: Create a cursor to execute SQL queries
        cursor = connection.cursor()

        # Step 3: Drop table if it already exists (for clean insertion)
        cursor.execute(f"DROP TABLE IF EXISTS {table_name};")
        print(f"Table `{table_name}` dropped if it existed.")

        # Step 4: Create a table structure to match CSV file
        create_table_query = f"""
        CREATE TABLE {table_name} (
            order_id VARCHAR(50),
            payment_sequential INT,
            payment_type VARCHAR(20),
            payment_installments INT,
            payment_value FLOAT
        );
        """
        cursor.execute(create_table_query)
        print(f"Table `{table_name}` created successfully!")

        # Step 5: Load the CSV data into pandas DataFrame
        data = pd.read_csv(csv_file_path)
        print("CSV data loaded into pandas DataFrame.")

        # Step 6: Insert data in batches of 100 records
        batch_size = 100  # Define the batch size
        total_records = len(data)  # Get total records in the DataFrame

        print(f"Starting data insertion into `{table_name}` in batches of {batch_size} records.")
        
        # Calculate the end index for the current batch example: if start=0 and batch_size=100, then end=100, so we will insert records from index 0 to 99 (100 records) in the first batch.
        for start in range(0, total_records, batch_size):
            
            # Calculate the end index for the current batch, how output looks like , for example: if start=0 and batch_size=100, then end=100, so we will insert records from index 0 to 99 (100 records) in the first batch.
            end = start + batch_size 
            
            # Get the current batch of records using iloc, which allows us to slice the DataFrame based on integer location. For example, if start=0 and end=100, then data.iloc[0:100] will return the first 100 records (index 0 to 99) from the DataFrame.
            
            batch = data.iloc[start:end]  
            
            # Convert batch to list of tuples for MySQL insertion
            # output looks like: [(order_id1, payment_sequential1, payment_type1, payment_installments1, payment_value1), (order_id2, payment_sequential2, payment_type2, payment_installments2, payment_value2), ...]
            batch_records = [tuple(row) for row in batch.itertuples(index=False, name=None)]

            # Prepare the INSERT query
            insert_query = f"""
            INSERT INTO {table_name}
            (order_id, payment_sequential, payment_type, payment_installments, payment_value)
            VALUES (%s, %s, %s, %s, %s); 
            """

            # Execute the insertion query for the batch
            cursor.executemany(insert_query, batch_records)
            connection.commit()  # Commit after each batch
            print(f"Inserted records {start + 1} to {min(end, total_records)} successfully.")

        print(f"All {total_records} records inserted successfully into `{table_name}`.")

except Error as e:
    # Step 7: Handle any errors
    print("Error while connecting to MySQL or inserting data:", e)

finally:
    # Step 8: Close the cursor and connection
    if connection.is_connected():
        cursor.close()
        connection.close()
        print("MySQL connection is closed.")
     