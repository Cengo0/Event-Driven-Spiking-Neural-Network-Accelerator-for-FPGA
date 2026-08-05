import torch

def analyze_model(file_path):
    print("="*50)
    print(f"🔍 ANALYZING MODEL: {file_path}")
    print("="*50)
    
    try:
        # Load the PyTorch state dictionary
        state_dict = torch.load(file_path, map_location=torch.device('cpu'))
        
        total_params = 0
        print(f"{'Layer Name':<35} | {'Shape':<20} | {'Total Weights'}")
        print("-" * 75)
        
        for key, tensor in state_dict.items():
            shape_str = str(list(tensor.shape))
            num_weights = tensor.numel()
            total_params += num_weights
            print(f"{key:<35} | {shape_str:<20} | {num_weights}")
            
        print("-" * 75)
        print(f"Total Model Parameters: {total_params}")
        
    except Exception as e:
        print(f"Error loading model: {e}")

if __name__ == "__main__":
    # Point this to your downloaded model file
    model_path = "small_mnist_clean_T_8_l2[0.000500].pth" 
    analyze_model(model_path)