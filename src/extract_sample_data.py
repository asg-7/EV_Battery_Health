import pandas as pd
import os

def extract_datasets():
    metadata_path = "data/cleaned_dataset/metadata.csv"
    data_dir = "data/cleaned_dataset/data"
    output_dir = "Sample data"
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"Reading metadata from {metadata_path}...")
    if not os.path.exists(metadata_path):
        print(f"Error: Metadata file not found at {metadata_path}")
        return
        
    metadata = pd.read_csv(metadata_path)
    battery_ids = ['B0005', 'B0006', 'B0007', 'B0018']
    
    for bid in battery_ids:
        print(f"\nProcessing battery {bid}...")
        # Filter for discharge type and battery ID
        subset = metadata[(metadata['battery_id'] == bid) & (metadata['type'] == 'discharge')].copy()
        
        # Parse start_time to sort chronologically. 
        # start_time is in format e.g. [2010.       7.      21.      15.       0.      35.093]
        # We can sort by test_id/uid as it's sequential.
        subset = subset.sort_values(by='uid')
        
        records = []
        for idx, (_, row) in enumerate(subset.iterrows(), 1):
            filename = row['filename']
            capacity = row['Capacity']
            filepath = os.path.join(data_dir, filename)
            
            if os.path.exists(filepath):
                try:
                    cycle_df = pd.read_csv(filepath)
                    # We need to average Voltage_measured, Current_measured, Temperature_measured
                    # across the discharge cycle to create a cycle-level summary data point.
                    v_mean = cycle_df['Voltage_measured'].mean()
                    c_mean = cycle_df['Current_measured'].mean()
                    t_mean = cycle_df['Temperature_measured'].mean()
                    
                    records.append({
                        'Voltage_measured': v_mean,
                        'Current_measured': c_mean,
                        'Temperature_measured': t_mean,
                        'Capacity': capacity,
                        'cycle': idx
                    })
                except Exception as e:
                    print(f"  Error reading {filepath}: {e}")
            else:
                print(f"  File not found: {filepath}")
                
        if records:
            df_out = pd.DataFrame(records)
            output_path = os.path.join(output_dir, f"NASA_Battery_{bid}.csv")
            df_out.to_csv(output_path, index=False)
            print(f"  Successfully saved {output_path} with {len(df_out)} cycles")
        else:
            print(f"  No records found for battery {bid}")

if __name__ == "__main__":
    extract_datasets()
