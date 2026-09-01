import pandas as pd
import matplotlib.pyplot as plt

def main():
    print("Reading simulation output...")
    # Read the CSV-style output from Verilog
    df = pd.read_csv('physical_output_spikes.txt')
    
    # Save directly to parquet (Standard format for MIA / TVLA side-channel tools)
    parquet_filename = 'data/cache/batch=00001.parquet'
    df.to_parquet(parquet_filename, engine='pyarrow')
    print(f"Saved temporal data to {parquet_filename}")
    
    # --- Plot 1: Cycle-by-Cycle Temporal Plot (Image 0) ---
    img0_df = df[df['Image_ID'] == 0]
    plt.figure(figsize=(10, 4))
    plt.scatter(img0_df['Clock_Cycle'], img0_df['Neuron_ID'], marker='|', color='red')
    plt.title('Temporal Leakage Signature: Cycle-by-Cycle Spiking Activity (Image 0)')
    plt.xlabel('Hardware Clock Cycle')
    plt.ylabel('Firing Neuron ID')
    plt.grid(True, linestyle='--', alpha=0.6)
    plt.tight_layout()
    plt.savefig('physical_temporal_cycle_plot.png', dpi=150)
    
    # --- Plot 2: Image-by-Image Cross-Sectional Plot ---
    activity_counts = df.groupby('Image_ID').size()
    plt.figure(figsize=(10, 4))
    activity_counts.plot(kind='bar', color='blue', alpha=0.7)
    plt.title('Data-Dependent Leakage: Total Output Spiking Volume per Image')
    plt.xlabel('Image Index')
    plt.ylabel('Total Spikes (Proxy for Dynamic Power)')
    plt.xticks(rotation=0)
    plt.grid(True, axis='y', linestyle='--', alpha=0.6)
    plt.tight_layout()
    plt.savefig('physical_image_cross_sectional_plot.png', dpi=150)
    
    print("Plots generated: temporal_cycle_plot.png and image_cross_sectional_plot.png")

if __name__ == '__main__':
    main()