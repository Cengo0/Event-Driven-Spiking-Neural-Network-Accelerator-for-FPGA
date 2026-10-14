python3 -c '
import numpy as np

data = np.load("data/cache/mnist_cnn3_deployment.npz")
w1_f = data["w1_f"]
b1_f = data["b1_f"]
q_conv2_w = data["q_conv2_w"]
q_fc_w = data["q_fc_w"]
test_imgs = data["test_imgs"][:5]
test_lbls = data["test_lbls"][:5]
hw_threshold = int(data["hw_threshold"])

for i in range(5):
    img = test_imgs[i]
    px_quant = np.clip(np.round(img * 256.0), -32768, 32767).astype(np.float32) / 256.0

    cnn_line_buf = np.zeros((2, 28), dtype=np.float32)
    cnn_win = np.zeros((3, 3), dtype=np.float32)
    cnn_v_mem = np.zeros((8, 28, 28), dtype=np.float32)
    v2_hw = np.zeros((16, 7, 7), dtype=np.float32)
    v3_hw = np.zeros(10, dtype=np.float32)
    spk3_hw = np.zeros(10, dtype=np.int32)
    l2_spk_count = 0

    for t in range(4):
        for idx in range(784):
            r = idx // 28
            c = idx % 28
            pixel_val = px_quant[r, c]

            for row in range(3):
                cnn_win[row, 0] = cnn_win[row, 1]
                cnn_win[row, 1] = cnn_win[row, 2]

            cnn_win[0, 2] = cnn_line_buf[0, c] if r >= 2 else 0.0
            cnn_win[1, 2] = cnn_line_buf[1, c] if r >= 1 else 0.0
            cnn_win[2, 2] = pixel_val

            cnn_line_buf[0, c] = cnn_line_buf[1, c]
            cnn_line_buf[1, c] = pixel_val

            if r >= 1 and c >= 1:
                y = r - 1
                x = c - 1
                for k in range(8):
                    acc = b1_f[k]
                    for dy in range(3):
                        for dx in range(3):
                            acc += w1_f[k, 0, dy, dx] * cnn_win[dy, dx]

                    cnn_v_mem[k, y, x] += acc
                    if cnn_v_mem[k, y, x] >= 1.0:
                        cnn_v_mem[k, y, x] -= 1.0
                        py = y >> 1
                        px = x >> 1
                        for co in range(16):
                            for dy2 in [-1, 0, 1]:
                                for dx2 in [-1, 0, 1]:
                                    oy = py + dy2
                                    ox = px + dx2
                                    if 0 <= oy < 14 and 0 <= ox < 14:
                                        y2 = oy >> 1
                                        x2 = ox >> 1
                                        wt = q_conv2_w[co, k, 1 - dy2, 1 - dx2]
                                        v2_hw[co, y2, x2] += wt
                                        # EVENT-DRIVEN FIRING: fires immediately when threshold crossed!
                                        if v2_hw[co, y2, x2] >= hw_threshold:
                                            v2_hw[co, y2, x2] = 0.0  # reset to 0
                                            l2_spk_count += 1
                                            # Route immediately to Layer 3!
                                            global_src = co * 49 + y2 * 7 + x2
                                            for dst in range(10):
                                                w_fc = q_fc_w[dst, global_src]
                                                v3_hw[dst] += w_fc
                                                if v3_hw[dst] < 0:
                                                    v3_hw[dst] = 0.0
                                                if v3_hw[dst] >= hw_threshold:
                                                    v3_hw[dst] = 0.0
                                                    spk3_hw[dst] += 1

    pred = int(np.argmax(spk3_hw)) if np.sum(spk3_hw) > 0 else 0
    mark = "✓" if pred == test_lbls[i] else "✗"
    print(f"Img {i} | True: {test_lbls[i]} | Pred: {pred} {mark} | L2 Spikes: {l2_spk_count} | L3 Spikes: {spk3_hw.tolist()}")
'