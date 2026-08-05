import torch
import numpy as np

def extract_to_npy(file_path, target_layer, output_filename):
    print(f"📦 Extracting '{target_layer}' from {file_path}...")
    
    state_dict = torch.load(file_path, map_location=torch.device('cpu'))
    
    if target_layer not in state_dict:
        print(f"❌ Error: {target_layer} not found in model!")
        print("Available layers:", list(state_dict.keys()))
        return

    # Extract the raw float weights
    raw_weights = state_dict[target_layer].numpy()
    
    # Save the raw floating-point weights for safety
    np.save(output_filename, raw_weights)
    
    print(f"✅ Successfully saved {raw_weights.size} weights to {output_filename}")
    print(f"   Shape: {raw_weights.shape}")
    print(f"   Min val: {raw_weights.min():.4f}, Max val: {raw_weights.max():.4f}")

if __name__ == "__main__":
    model_path = "small_mnist_clean_T_8_l2[0.000500].pth"
    
    # We will extract the first convolutional layer as a test
    # (From the source code, this is in 'features.0.weight')
    extract_to_npy(model_path, "features.0.weight", "mnist_features_0.npy")
    
    # Optional: Extract the first linear layer too
    extract_to_npy(model_path, "classifier.1.weight", "mnist_classifier_1.npy")