# Render benchmark

Measured with `beatframe bench` (real Manim renders; Manim's own cache off; each clip rendered once
uncached in an empty folder, then requested again from the same folder to time Beatframe's clip cache).
Peak memory is the Manim process's peak RSS (from the OS, `wait4`); CPU % is its CPU time / wall time.
Everything ran with the new defaults: one Manim process at a time, priority nice 10.

**Machine:** the cloud test container, 2 vCPU Intel Xeon 2.8 GHz, 7 GB RAM, Manim 0.21.0, Python 3.12.
This is *not* your HP ProBook (Ryzen + Radeon 680M), so the times are not laptop times. Your own
reference (one neural animation at 1080p30: 6.1 s, 537 MiB peak) suggests the laptop renders faster
than this 2-vCPU container; memory per process should be similar. Run
`beatframe bench neural_impulse bone_conduction --preset eco --preset quality` on the laptop for its own
numbers; every real render there also records its cost in `build/render_stats.jsonl`.

## Summary (6-second clips)

| group | preset | format | render time median / max | peak memory median / max | CPU | cached |
|---|---|---|---|---|---|---|
| 20 new templates | Eco 480p15 | long | 7.7 s / 12.6 s | 249 / 300 MiB | 108 % | ≤ 0.02 s |
| 20 new templates | Eco 480p15 | short | 7.5 s / 14.3 s | 242 / 312 MiB | 108 % | ≤ 0.02 s |
| 20 new templates | Quality 1080p30 | long | 16.6 s / 22.9 s | 617 / 717 MiB | 128 % | ≤ 0.02 s |
| 20 new templates | Quality 1080p30 | short | 16.4 s / 24.4 s | 591 / 692 MiB | 128 % | ≤ 0.02 s |
| existing (nerve_race, statement, stat_pop) | Quality 1080p30 | long | 15.8 s / 19.4 s | 661 / 684 MiB | 139 % | ≤ 0.02 s |

All 92 renders succeeded at the expected sizes (854x480@15, 480x854@15, 1920x1080@30, 1080x1920@30).
Slowest: `stress_response` and `sleep_cycle` (per-frame heart-rate / brainwave updates), about 23-24 s
here for 6 s of 1080p.

## What changed for laptop stability

| change | before | after |
|---|---|---|
| Manim processes at once | CPU cores ÷ 2 (8 on a 16-thread laptop CPU) | **1** (Settings or `BEATFRAME_WORKERS`) |
| priority | normal | nice 10 |
| Manim frame queue | unbounded: fast, simple scenes queued raw 1080p frames faster than they were encoded (`oxygen_exchange`: **1104-1124 MiB** peak) | capped at 12 frames (`oxygen_exchange`: **710 MiB**; other scenes unchanged or lower; same speed) |
| stopping a render | not possible | ■ Stop render kills the running Manim process; finished clips stay cached |

At the old default, 8 parallel 1080p processes at 600-700 MiB each would need about 5 GB of RAM plus all
CPU threads, which fits the freezes you saw. With one process the peak is about 0.7 GB.

## Full results

| template | format | preset | output | clip s | render s | cached s | peak RSS MiB | CPU % | MB | status |
|---|---|---|---|---|---|---|---|---|---|---|
| neural_impulse | long | eco | 854x480@15.0 | 6.0 | 6.2 | 0.001 | 212.5 | 108 | 0.32 | ok |
| neural_impulse | long | quality | 1920x1080@30.0 | 6.0 | 19.31 | 0.003 | 497.2 | 123 | 0.88 | ok |
| neural_impulse | short | eco | 480x854@15.0 | 6.0 | 6.41 | 0.001 | 207.6 | 107 | 0.28 | ok |
| neural_impulse | short | quality | 1080x1920@30.0 | 6.0 | 16.51 | 0.005 | 476.4 | 130 | 0.77 | ok |
| memory_reconstruction | long | eco | 854x480@15.0 | 6.0 | 6.92 | 0.003 | 234.3 | 110 | 0.23 | ok |
| memory_reconstruction | long | quality | 1920x1080@30.0 | 6.0 | 15.56 | 0.004 | 562.0 | 135 | 0.66 | ok |
| memory_reconstruction | short | eco | 480x854@15.0 | 6.0 | 6.82 | 0.002 | 238.4 | 111 | 0.22 | ok |
| memory_reconstruction | short | quality | 1080x1920@30.0 | 6.0 | 18.36 | 0.004 | 581.3 | 126 | 0.63 | ok |
| attention_spotlight | long | eco | 854x480@15.0 | 6.0 | 6.77 | 0.004 | 278.5 | 109 | 0.21 | ok |
| attention_spotlight | long | quality | 1920x1080@30.0 | 6.0 | 15.46 | 0.005 | 716.8 | 131 | 0.57 | ok |
| attention_spotlight | short | eco | 480x854@15.0 | 6.0 | 6.77 | 0.004 | 230.8 | 108 | 0.18 | ok |
| attention_spotlight | short | quality | 1080x1920@30.0 | 6.0 | 15.54 | 0.004 | 630.8 | 130 | 0.49 | ok |
| sleep_cycle | long | eco | 854x480@15.0 | 6.0 | 12.55 | 0.001 | 268.4 | 106 | 0.15 | ok |
| sleep_cycle | long | quality | 1920x1080@30.0 | 6.0 | 22.93 | 0.007 | 626.5 | 127 | 0.42 | ok |
| sleep_cycle | short | eco | 480x854@15.0 | 6.0 | 14.31 | 0.003 | 249.3 | 105 | 0.13 | ok |
| sleep_cycle | short | quality | 1080x1920@30.0 | 6.0 | 22.67 | 0.011 | 577.4 | 129 | 0.4 | ok |
| stress_response | long | eco | 854x480@15.0 | 6.0 | 10.56 | 0.002 | 242.4 | 105 | 0.17 | ok |
| stress_response | long | quality | 1920x1080@30.0 | 6.0 | 21.64 | 0.013 | 552.5 | 117 | 0.46 | ok |
| stress_response | short | eco | 480x854@15.0 | 6.0 | 10.85 | 0.002 | 239.4 | 104 | 0.18 | ok |
| stress_response | short | quality | 1080x1920@30.0 | 6.0 | 24.4 | 0.009 | 533.7 | 118 | 0.46 | ok |
| bone_conduction | long | eco | 854x480@15.0 | 6.0 | 8.8 | 0.001 | 240.7 | 106 | 0.19 | ok |
| bone_conduction | long | quality | 1920x1080@30.0 | 6.0 | 18.44 | 0.004 | 600.2 | 125 | 0.53 | ok |
| bone_conduction | short | eco | 480x854@15.0 | 6.0 | 8.29 | 0.001 | 244.6 | 108 | 0.18 | ok |
| bone_conduction | short | quality | 1080x1920@30.0 | 6.0 | 18.96 | 0.004 | 636.2 | 128 | 0.51 | ok |
| inner_ear | long | eco | 854x480@15.0 | 6.0 | 7.2 | 0.003 | 237.1 | 110 | 0.25 | ok |
| inner_ear | long | quality | 1920x1080@30.0 | 6.0 | 14.88 | 0.004 | 635.3 | 132 | 0.63 | ok |
| inner_ear | short | eco | 480x854@15.0 | 6.0 | 6.79 | 0.005 | 233.2 | 108 | 0.2 | ok |
| inner_ear | short | quality | 1080x1920@30.0 | 6.0 | 15.5 | 0.006 | 611.1 | 127 | 0.51 | ok |
| retina_processing | long | eco | 854x480@15.0 | 6.0 | 7.6 | 0.003 | 248.5 | 109 | 0.26 | ok |
| retina_processing | long | quality | 1920x1080@30.0 | 6.0 | 17.37 | 0.006 | 573.8 | 131 | 0.71 | ok |
| retina_processing | short | eco | 480x854@15.0 | 6.0 | 8.06 | 0.003 | 250.2 | 108 | 0.25 | ok |
| retina_processing | short | quality | 1080x1920@30.0 | 6.0 | 16.87 | 0.005 | 569.8 | 130 | 0.69 | ok |
| touch_receptors | long | eco | 854x480@15.0 | 6.0 | 8.8 | 0.008 | 274.8 | 105 | 0.13 | ok |
| touch_receptors | long | quality | 1920x1080@30.0 | 6.0 | 17.01 | 0.004 | 669.8 | 128 | 0.34 | ok |
| touch_receptors | short | eco | 480x854@15.0 | 6.0 | 7.52 | 0.004 | 278.3 | 107 | 0.13 | ok |
| touch_receptors | short | quality | 1080x1920@30.0 | 6.0 | 17.71 | 0.005 | 605.0 | 128 | 0.33 | ok |
| reflex_arc | long | eco | 854x480@15.0 | 6.0 | 7.08 | 0.004 | 243.1 | 111 | 0.24 | ok |
| reflex_arc | long | quality | 1920x1080@30.0 | 6.0 | 17.01 | 0.003 | 657.3 | 128 | 0.66 | ok |
| reflex_arc | short | eco | 480x854@15.0 | 6.0 | 6.57 | 0.004 | 236.1 | 111 | 0.19 | ok |
| reflex_arc | short | quality | 1080x1920@30.0 | 6.0 | 15.44 | 0.006 | 569.4 | 134 | 0.51 | ok |
| blind_spot_test | long | eco | 854x480@15.0 | 6.0 | 8.6 | 0.003 | 299.8 | 105 | 0.16 | ok |
| blind_spot_test | long | quality | 1920x1080@30.0 | 6.0 | 15.3 | 0.008 | 664.6 | 125 | 0.43 | ok |
| blind_spot_test | short | eco | 480x854@15.0 | 6.0 | 8.71 | 0.005 | 291.1 | 105 | 0.15 | ok |
| blind_spot_test | short | quality | 1080x1920@30.0 | 6.0 | 17.41 | 0.02 | 661.4 | 122 | 0.38 | ok |
| balance_experiment | long | eco | 854x480@15.0 | 6.0 | 10.03 | 0.003 | 285.6 | 109 | 0.13 | ok |
| balance_experiment | long | quality | 1920x1080@30.0 | 6.0 | 15.65 | 0.004 | 670.7 | 133 | 0.35 | ok |
| balance_experiment | short | eco | 480x854@15.0 | 6.0 | 7.58 | 0.003 | 253.5 | 107 | 0.11 | ok |
| balance_experiment | short | quality | 1080x1920@30.0 | 6.0 | 16.32 | 0.002 | 692.1 | 133 | 0.28 | ok |
| reaction_time | long | eco | 854x480@15.0 | 6.0 | 6.93 | 0.003 | 233.5 | 103 | 0.2 | ok |
| reaction_time | long | quality | 1920x1080@30.0 | 6.0 | 13.87 | 0.004 | 535.7 | 129 | 0.52 | ok |
| reaction_time | short | eco | 480x854@15.0 | 6.0 | 6.22 | 0.002 | 233.9 | 110 | 0.18 | ok |
| reaction_time | short | quality | 1080x1920@30.0 | 6.0 | 16.13 | 0.004 | 562.9 | 126 | 0.47 | ok |
| stroop_effect | long | eco | 854x480@15.0 | 6.0 | 6.43 | 0.003 | 243.8 | 107 | 0.27 | ok |
| stroop_effect | long | quality | 1920x1080@30.0 | 6.0 | 13.1 | 0.007 | 593.6 | 127 | 0.59 | ok |
| stroop_effect | short | eco | 480x854@15.0 | 6.0 | 6.21 | 0.002 | 232.4 | 106 | 0.27 | ok |
| stroop_effect | short | quality | 1080x1920@30.0 | 6.0 | 15.2 | 0.006 | 581.1 | 123 | 0.61 | ok |
| ring_finger_test | long | eco | 854x480@15.0 | 6.0 | 6.54 | 0.003 | 249.3 | 107 | 0.17 | ok |
| ring_finger_test | long | quality | 1920x1080@30.0 | 6.0 | 14.98 | 0.008 | 618.3 | 125 | 0.38 | ok |
| ring_finger_test | short | eco | 480x854@15.0 | 6.0 | 5.98 | 0.001 | 238.3 | 106 | 0.16 | ok |
| ring_finger_test | short | quality | 1080x1920@30.0 | 6.0 | 15.24 | 0.003 | 601.0 | 128 | 0.39 | ok |
| blood_circulation | long | eco | 854x480@15.0 | 6.0 | 12.33 | 0.004 | 275.1 | 109 | 0.12 | ok |
| blood_circulation | long | quality | 1920x1080@30.0 | 6.0 | 18.98 | 0.001 | 626.3 | 133 | 0.34 | ok |
| blood_circulation | short | eco | 480x854@15.0 | 6.0 | 10.46 | 0.006 | 309.4 | 109 | 0.12 | ok |
| blood_circulation | short | quality | 1080x1920@30.0 | 6.0 | 18.53 | 0.001 | 628.3 | 137 | 0.34 | ok |
| oxygen_exchange | long | eco | 854x480@15.0 | 6.0 | 6.24 | 0.006 | 281.2 | 119 | 0.17 | ok |
| oxygen_exchange | long | quality | 1920x1080@30.0 | 6.0 | 13.16 | 0.001 | 675.2 | 141 | 0.48 | ok |
| oxygen_exchange | short | eco | 480x854@15.0 | 6.0 | 6.09 | 0.005 | 312.5 | 117 | 0.18 | ok |
| oxygen_exchange | short | quality | 1080x1920@30.0 | 6.0 | 12.53 | 0.001 | 664.3 | 140 | 0.49 | ok |
| dna_unzipping | long | eco | 854x480@15.0 | 6.0 | 8.95 | 0.005 | 265.1 | 108 | 0.14 | ok |
| dna_unzipping | long | quality | 1920x1080@30.0 | 6.0 | 17.33 | 0.002 | 616.6 | 130 | 0.34 | ok |
| dna_unzipping | short | eco | 480x854@15.0 | 6.0 | 9.12 | 0.004 | 269.5 | 108 | 0.11 | ok |
| dna_unzipping | short | quality | 1080x1920@30.0 | 6.0 | 16.06 | 0.007 | 605.0 | 128 | 0.28 | ok |
| immune_response | long | eco | 854x480@15.0 | 6.0 | 9.17 | 0.002 | 227.3 | 105 | 0.22 | ok |
| immune_response | long | quality | 1920x1080@30.0 | 6.0 | 19.61 | 0.008 | 528.6 | 125 | 0.6 | ok |
| immune_response | short | eco | 480x854@15.0 | 6.0 | 10.3 | 0.006 | 216.8 | 104 | 0.2 | ok |
| immune_response | short | quality | 1080x1920@30.0 | 6.0 | 22.29 | 0.008 | 540.7 | 120 | 0.55 | ok |
| evolution_tree | long | eco | 854x480@15.0 | 6.0 | 7.75 | 0.002 | 260.9 | 108 | 0.21 | ok |
| evolution_tree | long | quality | 1920x1080@30.0 | 6.0 | 16.25 | 0.003 | 548.2 | 130 | 0.48 | ok |
| evolution_tree | short | eco | 480x854@15.0 | 6.0 | 7.64 | 0.004 | 265.1 | 109 | 0.19 | ok |
| evolution_tree | short | quality | 1080x1920@30.0 | 6.0 | 14.53 | 0.001 | 527.5 | 130 | 0.46 | ok |
| nerve_race | long | eco | 854x480@15.0 | 6.0 | 8.24 | 0.003 | 254.7 | 107 | 0.1 | ok |
| nerve_race | long | quality | 1920x1080@30.0 | 6.0 | 19.37 | 0.004 | 637.2 | 126 | 0.28 | ok |
| nerve_race | short | eco | 480x854@15.0 | 6.0 | 11.43 | 0.006 | 247.0 | 106 | 0.07 | ok |
| nerve_race | short | quality | 1080x1920@30.0 | 6.0 | 20.71 | 0.009 | 612.1 | 127 | 0.19 | ok |
| statement | long | eco | 854x480@15.0 | 6.0 | 6.44 | 0.006 | 263.6 | 114 | 0.11 | ok |
| statement | long | quality | 1920x1080@30.0 | 6.0 | 12.72 | 0.002 | 660.9 | 144 | 0.31 | ok |
| statement | short | eco | 480x854@15.0 | 6.0 | 6.12 | 0.007 | 304.0 | 117 | 0.1 | ok |
| statement | short | quality | 1080x1920@30.0 | 6.0 | 17.07 | 0.023 | 692.3 | 133 | 0.29 | ok |
| stat_pop | long | eco | 854x480@15.0 | 6.0 | 9.13 | 0.007 | 273.2 | 108 | 0.09 | ok |
| stat_pop | long | quality | 1920x1080@30.0 | 6.0 | 15.79 | 0.003 | 683.5 | 139 | 0.29 | ok |
| stat_pop | short | eco | 480x854@15.0 | 6.0 | 6.66 | 0.01 | 301.9 | 116 | 0.09 | ok |
| stat_pop | short | quality | 1080x1920@30.0 | 6.0 | 17.92 | 0.014 | 696.7 | 137 | 0.29 | ok |

