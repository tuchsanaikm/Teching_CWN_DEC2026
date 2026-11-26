# LAB 6 - cost of the rented machine (label vapp-lab6-nginx)

- instance <id> (Quebec, CA), 2x RTX 3090, 40 GB disk, destroyed 2026-11-23
- lifetime: created 2026-11-23 00:46:55 UTC, destroyed 02:50:56 UTC = 7442 s = 2 h 04 min (2.067 h)
- price: $0.3578 / hour (GPU $0.3467 + disk $0.0111), download $0.0065 / GB
- lifetime x price = 2.067 h x $0.3578 = $0.740 (+ about $0.003 download)
- charged in Vast.ai billing (`vastai show invoices-v1 --charges`, read about 10 minutes after the destroy): $0.644
  = GPU 1.790 h $0.621 + disk 1.797 h $0.020 + download 0.4 GB $0.003.
  The billing entry was still behind the lifetime at that time (1.79 h of 2.07 h), so the final charge may rise to about $0.74.
- after the destroy `vastai show instances` returned an empty list.
