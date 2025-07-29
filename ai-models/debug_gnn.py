import torch
import torch.nn as nn
import numpy as np
from src.temporal_causal_gnn import TemporalCausalGNN, prepare_simulation_data

print("=== Debugging TemporalCausalGNN tensor dimensions ===")

market_data = np.random.randn(1000, 10)
sampled_data, edge_index = prepare_simulation_data(market_data, lookback_days=30, num_samples=500)

print(f"Sampled data shape: {sampled_data.shape}")
print(f"Edge index shape: {edge_index.shape}")

gnn = TemporalCausalGNN(num_features=10, num_nodes=10, hidden_dim=64)

x = torch.randn(10, 10)  # 10 nodes, 10 features
timestamps = torch.randn(10, 1)

print(f"\nInput shapes:")
print(f"x shape: {x.shape}")
print(f"timestamps shape: {timestamps.shape}")
print(f"edge_index shape: {edge_index.shape}")

print(f"\n=== Step-by-step tensor flow ===")

time_emb = torch.relu(gnn.time_embed(timestamps))
print(f"Time embedding shape: {time_emb.shape}")

x_with_time = x + time_emb
print(f"x + time_emb shape: {x_with_time.shape}")

x1 = torch.relu(gnn.gat1(x_with_time))
print(f"After gat1 shape: {x1.shape}")

x2 = gnn.dropout(x1)
print(f"After dropout shape: {x2.shape}")

x3 = torch.relu(gnn.gat2(x2))
print(f"After gat2 shape: {x3.shape}")

output_raw = gnn.output(x3)
print(f"Raw output shape: {output_raw.shape}")

output_squeezed = output_raw.squeeze(-1)
print(f"Squeezed output shape: {output_squeezed.shape}")

print(f"\n=== Full forward pass ===")
full_output = gnn(x, edge_index, timestamps)
print(f"Full forward output shape: {full_output.shape}")
print(f"Expected shape: (10,)")

print(f"\n=== Network architecture ===")
print(gnn)
