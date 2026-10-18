# Live evidence

Written by `python scripts/verify.py`, which reads everything below off GenLayer Studionet. Nothing here is a transcript: re-run it and the network answers again. It needs no key, no funds and no GenLayer account.

| | |
|---|---|
| Network | GenLayer Studionet, chain 61999 |
| RPC | `https://studio.genlayer.com/api` |
| Contract | [`0xB70040Bca306122b795F7Cd9d7623aCe9175067B`](https://explorer-studio.genlayer.com/address/0xB70040Bca306122b795F7Cd9d7623aCe9175067B) |
| Deployer | `0x31f8AD449d0D1a6f3A13D00e9190411576271888` |
| Source commit | `5a464a2` |
| Contract source | `contracts/trustroute.py`, 136524 bytes, sha256 `197fba21c20d17eb81c24e19eecd88025be61355623ab31fca303f41057ce9ca` |
| Deployed bytes | 136524 bytes, sha256 `197fba21c20d17eb81c24e19eecd88025be61355623ab31fca303f41057ce9ca` |
| Deployed = committed source | **yes, byte-identical** |

## The records, re-fetched

Each one is bound to the sha256 of its exact bytes. Change a byte and the contract reports `HASH_MISMATCH` instead of reading it, so these hashes are what the adjudications actually rest on.

| Record | Bytes | sha256 | Still publishes those bytes |
|---|---|---|---|
| `bill-of-lading.txt` | 690 | `a21c29edfd30b35b...` | yes |
| `condition-log-compliant.txt` | 798 | `3db875da6dcd013a...` | yes |
| `condition-log-excursion.txt` | 845 | `38ce32a19200208c...` | yes |
| `custody-scan-destination-out-of-order.txt` | 733 | `a403264a598e8cad...` | yes |
| `custody-scan-destination.txt` | 692 | `9a95bd11ab77c03c...` | yes |
| `custody-scan-directed.txt` | 895 | `29cc22f19692e51b...` | yes |
| `custody-scan-origin.txt` | 764 | `53ab95dcf00acd94...` | yes |
| `custody-scan-transit.txt` | 716 | `1d300d08ebc3f1bb...` | yes |
| `customs-entry.txt` | 664 | `caa1844aeb9af2df...` | yes |
| `delivery-confirmation.txt` | 559 | `91127d7d7f793554...` | yes |
| `inspection-certificate.txt` | 757 | `8af00a86c32b36ab...` | yes |
| `origin-certificate.txt` | 660 | `758a0960830ca2c2...` | yes |
| `warehouse-receipt-conflicting-lot.txt` | 551 | `d28bbfe55b14a461...` | yes |
| `warehouse-receipt.txt` | 551 | `543192989bd9f843...` | yes |

## Every transaction, re-queried

A round whose validators do not reach a majority commits nothing and still reports success, so the lifecycle and the votes are read here rather than taken from the run that made them.

| What | Transaction | Lifecycle | Execution | Consensus |
|---|---|---|---|---|
| register pol-cold-ok-5a464a-4437 | [`0xa1aadb2eff7d42a3...`](https://explorer-studio.genlayer.com/tx/0xa1aadb2eff7d42a3e217e6e5cd97a0a74f5a023c796be4405242ac52946e31a1) | FINALIZED | SUCCESS | 3 agree, 0 disagree, 2 idle of 5 |
| publish pol-cold-ok-5a464a-4437 | [`0xa59775cc0faa172f...`](https://explorer-studio.genlayer.com/tx/0xa59775cc0faa172fc17bd7611fe6cc47cc95852ecdd093ffb0e48cc54ac27019) | FINALIZED | SUCCESS | 3 agree, 0 disagree, 2 idle of 5 |
| open chal-cold-ok-5a464a-4437 | [`0x7703e03e41181bc2...`](https://explorer-studio.genlayer.com/tx/0x7703e03e41181bc2671677b63ce077d3b84233f38a4036e2d6232f1346ebbd9d) | FINALIZED | SUCCESS | 3 agree, 0 disagree, 2 idle of 5 |
| submit sub-cold-ok | [`0x7f2aa7318d3f7caa...`](https://explorer-studio.genlayer.com/tx/0x7f2aa7318d3f7caa2254cc2f9a98b181988d35755bfb0ef59da1847e6087befd) | FINALIZED | SUCCESS | 3 agree, 0 disagree, 2 idle of 5 |
| resolve sub-cold-ok | [`0x8745eeef06903b25...`](https://explorer-studio.genlayer.com/tx/0x8745eeef06903b255e2114aefc1b95a5c2ca1824ea789f044f22cddde35c7688) | FINALIZED | SUCCESS | 3 agree, 0 disagree, 2 idle of 5 |
| register pol-cold-exc-5a464a-4437 | [`0x59ba60ebf8f84a4c...`](https://explorer-studio.genlayer.com/tx/0x59ba60ebf8f84a4cdae06de80f7ed5836c80e8ac868c764c94168097a70726ed) | FINALIZED | SUCCESS | 3 agree, 0 disagree, 2 idle of 5 |
| publish pol-cold-exc-5a464a-4437 | [`0x4ba0b0b38f161a63...`](https://explorer-studio.genlayer.com/tx/0x4ba0b0b38f161a6363c720fec7a67634c1bb7e0c1224eaa7a0a0133815499a80) | FINALIZED | SUCCESS | 3 agree, 0 disagree, 2 idle of 5 |
| open chal-cold-exc-5a464a-4437 | [`0x7e8345f0e8a603f3...`](https://explorer-studio.genlayer.com/tx/0x7e8345f0e8a603f3f5082d448496317ec7ba1c23f32b2ffe966a2f6271298aaa) | FINALIZED | SUCCESS | 3 agree, 0 disagree, 2 idle of 5 |
| submit sub-cold-exc | [`0x3f5067370f3d0cbc...`](https://explorer-studio.genlayer.com/tx/0x3f5067370f3d0cbc67bf9645b0843680a1bb4a02caa7ffea0a2e102b98b37f5d) | FINALIZED | SUCCESS | 5 agree, 0 disagree, 0 idle of 5 |
| resolve sub-cold-exc | [`0xe4355ce985aaef1c...`](https://explorer-studio.genlayer.com/tx/0xe4355ce985aaef1c844ee5e6c9e087f8d5212f6901be0bcc09a0322bb0e8429f) | FINALIZED | SUCCESS | 3 agree, 1 disagree, 1 idle of 5 |
| register pol-cust-ooo-5a464a-4437 | [`0x5c5dedc7683a0b07...`](https://explorer-studio.genlayer.com/tx/0x5c5dedc7683a0b0722a7b846375d9fb661436fb416b3800cecdb56033e112ad6) | FINALIZED | SUCCESS | 3 agree, 0 disagree, 2 idle of 5 |
| publish pol-cust-ooo-5a464a-4437 | [`0x11a51296fff0ccd5...`](https://explorer-studio.genlayer.com/tx/0x11a51296fff0ccd5f9fc18fb57ae83c50c46567d67c25b94fb1fc4e9bc7ab8c3) | FINALIZED | SUCCESS | 3 agree, 0 disagree, 2 idle of 5 |
| open chal-cust-ooo-5a464a-4437 | [`0xa7afb5a50249571f...`](https://explorer-studio.genlayer.com/tx/0xa7afb5a50249571fdb69923c008ef2029c4a4d274fdf10faa7b7966e5b1bd8a5) | FINALIZED | SUCCESS | 3 agree, 0 disagree, 2 idle of 5 |
| submit sub-cust-ooo | [`0x6b5317cd210b1b7e...`](https://explorer-studio.genlayer.com/tx/0x6b5317cd210b1b7ec38e5e344371b15ea32990a93893fc4b86fa33ce2a7fba84) | FINALIZED | SUCCESS | 3 agree, 0 disagree, 2 idle of 5 |
| resolve sub-cust-ooo | [`0x0fe01bbf0d14c1f1...`](https://explorer-studio.genlayer.com/tx/0x0fe01bbf0d14c1f1789d8444fb44c5f9215d53334f60762c45788e0a8597fdca) | FINALIZED | SUCCESS | 3 agree, 0 disagree, 2 idle of 5 |
| register pol-cust-conf-5a464a-4437 | [`0x896b7c00fc89dc5a...`](https://explorer-studio.genlayer.com/tx/0x896b7c00fc89dc5a157737497b9ca8c98580db8365f4fc39101a364afba9d64e) | FINALIZED | SUCCESS | 3 agree, 0 disagree, 2 idle of 5 |
| publish pol-cust-conf-5a464a-4437 | [`0x4f46fbd6265ef32e...`](https://explorer-studio.genlayer.com/tx/0x4f46fbd6265ef32e778b96c2aadcbc1409742ecae0aa7d87abade078595909a1) | FINALIZED | SUCCESS | 3 agree, 0 disagree, 2 idle of 5 |
| open chal-cust-conf-5a464a-4437 | [`0x37f356cc58e81186...`](https://explorer-studio.genlayer.com/tx/0x37f356cc58e811865702414dfb71400ec331eb0a5dc2c8807605cbbcb6e197d6) | FINALIZED | SUCCESS | 4 agree, 0 disagree, 1 idle of 5 |
| submit sub-cust-conf | [`0x9949fe97faff6486...`](https://explorer-studio.genlayer.com/tx/0x9949fe97faff64866a7da14066130a5bc4568fc6f1eeef93f3d990b49dc69cf7) | FINALIZED | SUCCESS | 3 agree, 0 disagree, 2 idle of 5 |
| resolve sub-cust-conf | [`0x4043f30482dd28c2...`](https://explorer-studio.genlayer.com/tx/0x4043f30482dd28c287a116d52ad84fb994ac7ee71d4e587dfdcce9bbb39f3a49) | FINALIZED | SUCCESS | 3 agree, 1 disagree, 1 idle of 5 |
| register pol-cust-dir-5a464a-4437 | [`0x813a4c02287ab324...`](https://explorer-studio.genlayer.com/tx/0x813a4c02287ab3244a0adabf16dad88248fa20f9ca8fe02423e803de293c5d13) | FINALIZED | SUCCESS | 5 agree, 0 disagree, 0 idle of 5 |
| publish pol-cust-dir-5a464a-4437 | [`0x8989292cb5797f97...`](https://explorer-studio.genlayer.com/tx/0x8989292cb5797f97bce188cd0f189cabfe45a032c395fb5491a7e63eee0c0c16) | FINALIZED | SUCCESS | 5 agree, 0 disagree, 0 idle of 5 |
| open chal-cust-dir-5a464a-4437 | [`0x1f9b1d6953f37d02...`](https://explorer-studio.genlayer.com/tx/0x1f9b1d6953f37d021b0dcc92cfc5c390964357fd988eb2907ea63c3534b5fa00) | FINALIZED | SUCCESS | 4 agree, 0 disagree, 1 idle of 5 |
| submit sub-cust-dir | [`0xb8a5300974fa3964...`](https://explorer-studio.genlayer.com/tx/0xb8a5300974fa3964045730e8ad72720e3c2a156fa4ce185cdc2a04b700c1c2c0) | FINALIZED | SUCCESS | 4 agree, 0 disagree, 1 idle of 5 |
| resolve sub-cust-dir | [`0x55277cdcd9d1552d...`](https://explorer-studio.genlayer.com/tx/0x55277cdcd9d1552d5b095dd525404538ca8afec1db8543e519ffaaa532777b60) | FINALIZED | SUCCESS | 3 agree, 0 disagree, 2 idle of 5 |
| register pol-origin-5a464a-4437 | [`0x3d4666160b1e51fd...`](https://explorer-studio.genlayer.com/tx/0x3d4666160b1e51fd3a4e402b08e1c78ab21be4af5953cbadf089d250b6b19236) | FINALIZED | SUCCESS | 3 agree, 0 disagree, 2 idle of 5 |
| publish pol-origin-5a464a-4437 | [`0x3315feb82ea89fae...`](https://explorer-studio.genlayer.com/tx/0x3315feb82ea89faef62ed67946876d8e8ef9f9ced363ad39663eb2e105c332c2) | FINALIZED | SUCCESS | 3 agree, 0 disagree, 2 idle of 5 |
| open chal-origin-5a464a-4437 | [`0xbf05c48853e4fdf0...`](https://explorer-studio.genlayer.com/tx/0xbf05c48853e4fdf0fe21385ac497f7a17d6e670f7e18a6d630e4869076ed25d5) | FINALIZED | SUCCESS | 3 agree, 0 disagree, 2 idle of 5 |
| submit sub-origin | [`0x94fc55418f71d299...`](https://explorer-studio.genlayer.com/tx/0x94fc55418f71d299d17f96e387297830c947e677a24205f26879efad66373625) | FINALIZED | SUCCESS | 3 agree, 0 disagree, 2 idle of 5 |
| resolve sub-origin | [`0x7b5362621386bf46...`](https://explorer-studio.genlayer.com/tx/0x7b5362621386bf46bc5c5d97c4bdf4cb4b8b45acee9c600a5c65a21bd45dfca6) | FINALIZED | SUCCESS | 3 agree, 0 disagree, 2 idle of 5 |
| register pol-cold-gone-5a464a-4437 | [`0xde7394857b84f8f1...`](https://explorer-studio.genlayer.com/tx/0xde7394857b84f8f15df4da986325cc497ee4ab57ac7b030f03b1eed3b51ce5c5) | FINALIZED | SUCCESS | 3 agree, 0 disagree, 2 idle of 5 |
| publish pol-cold-gone-5a464a-4437 | [`0x7b6cefeb6f730907...`](https://explorer-studio.genlayer.com/tx/0x7b6cefeb6f730907ef7df1d4557973582ff0e6b83e8230dde3890136eed8cc18) | FINALIZED | SUCCESS | 5 agree, 0 disagree, 0 idle of 5 |
| open chal-cold-gone-5a464a-4437 | [`0x9f50f9e353a4ea04...`](https://explorer-studio.genlayer.com/tx/0x9f50f9e353a4ea0462ab155dd4935404f0ab6e67bfc32bcd1b779660ed92fc5a) | FINALIZED | SUCCESS | 3 agree, 0 disagree, 2 idle of 5 |
| submit sub-cold-gone | [`0x6558a99e461f81ed...`](https://explorer-studio.genlayer.com/tx/0x6558a99e461f81eda15e98bfe80e84cb6db2b737667a0ecc366a70eaf0459a54) | FINALIZED | SUCCESS | 3 agree, 0 disagree, 2 idle of 5 |
| resolve sub-cold-gone | [`0x6b16dfac9364f7a4...`](https://explorer-studio.genlayer.com/tx/0x6b16dfac9364f7a463a9fe520d2cd82c47838eb5c1092bb0dd9505fb01748e1b) | FINALIZED | SUCCESS | 3 agree, 0 disagree, 2 idle of 5 |
| retry sub-cold-gone | [`0x4988fada604bb498...`](https://explorer-studio.genlayer.com/tx/0x4988fada604bb4985ad8dd2e5f1a734bee59c616d390b2621f39287b112b1830) | FINALIZED | SUCCESS | 5 agree, 0 disagree, 0 idle of 5 |

## What the contract stores

### A - a cold chain whose log holds the range across the window

| | | |
|---|---|---|
| submission | `sub-cold-ok-5a464a-4437` | OK |
| verdict | `CLAIM_SUPPORTED` | OK |
| status | `RESOLVED` | OK |
| evidence status | `EVIDENCE_SUFFICIENT` | OK |
| records present | `True` | OK |
| records consistent | `True` | OK |
| source authenticity verified | `True` | OK |
| required event supported | `True` | OK |
| identity state | `CONSISTENT` | OK |
| condition state | `HELD` | OK |
| authenticity state | `AUTHENTICATED_ORIGIN` | OK |
| directed text hits | `0` | OK |
| is_claim_supported | `True` | OK |
| freshness | `RELIABLE` | OK |

### B - a cold chain with an eighteen-hour excursion

| | | |
|---|---|---|
| submission | `sub-cold-exc-5a464a-4437` | OK |
| verdict | `CLAIM_NOT_ESTABLISHED` | OK |
| status | `RESOLVED` | OK |
| evidence status | `EVIDENCE_INSUFFICIENT` | OK |
| records present | `True` | OK |
| records consistent | `True` | OK |
| source authenticity verified | `True` | OK |
| required event supported | `False` | OK |
| identity state | `CONSISTENT` | OK |
| condition state | `BREACHED` | OK |
| authenticity state | `AUTHENTICATED_ORIGIN` | OK |
| directed text hits | `0` | OK |
| is_claim_supported | `False` | OK |
| freshness | `RELIABLE` | OK |

### C - a custody chain whose checkpoints are out of order

| | | |
|---|---|---|
| submission | `sub-cust-ooo-5a464a-4437` | OK |
| verdict | `INCONSISTENT_EVIDENCE` | OK |
| status | `RETRYABLE` | OK |
| evidence status | `EVIDENCE_CONTRADICTORY` | OK |
| records present | `True` | OK |
| records consistent | `False` | OK |
| source authenticity verified | `True` | OK |
| required event supported | `False` | OK |
| custody state | `OUT_OF_ORDER` | OK |
| identity state | `CONSISTENT` | OK |
| authenticity state | `AUTHENTICATED_ORIGIN` | OK |
| directed text hits | `0` | OK |
| is_claim_supported | `False` | OK |
| freshness | `UNKNOWN` | OK |

### D - records that disagree about which lot they describe

| | | |
|---|---|---|
| submission | `sub-cust-conf-5a464a-4437` | OK |
| verdict | `INCONSISTENT_EVIDENCE` | OK |
| status | `RETRYABLE` | OK |
| evidence status | `EVIDENCE_CONTRADICTORY` | OK |
| records present | `True` | OK |
| records consistent | `False` | OK |
| source authenticity verified | `True` | OK |
| required event supported | `True` | OK |
| custody state | `COMPLETE` | OK |
| identity state | `CONFLICTING` | OK |
| authenticity state | `AUTHENTICATED_ORIGIN` | OK |
| directed text hits | `0` | OK |
| is_claim_supported | `False` | OK |
| freshness | `UNKNOWN` | OK |

### E - a record that instructs whoever reads it

| | | |
|---|---|---|
| submission | `sub-cust-dir-5a464a-4437` | OK |
| verdict | `CLAIM_NOT_ESTABLISHED` | OK |
| status | `RESOLVED` | OK |
| evidence status | `EVIDENCE_SUFFICIENT` | OK |
| records present | `True` | OK |
| records consistent | `True` | OK |
| source authenticity verified | `True` | OK |
| required event supported | `True` | OK |
| custody state | `COMPLETE` | OK |
| identity state | `CONSISTENT` | OK |
| authenticity state | `AUTHENTICATED_ORIGIN` | OK |
| directed text hits | `6` | OK |
| is_claim_supported | `False` | OK |
| freshness | `RELIABLE` | OK |

### F - a certificate not served from its issuer's registered host

| | | |
|---|---|---|
| submission | `sub-origin-5a464a-4437` | OK |
| verdict | `CLAIM_NOT_ESTABLISHED` | OK |
| status | `RESOLVED` | OK |
| evidence status | `SOURCE_AUTHENTICITY_UNVERIFIED` | OK |
| records present | `True` | OK |
| records consistent | `True` | OK |
| source authenticity verified | `False` | OK |
| required event supported | `True` | OK |
| identity state | `CONSISTENT` | OK |
| origin state | `SUPPORTED` | OK |
| authenticity state | `SOURCE_UNVERIFIED` | OK |
| directed text hits | `0` | OK |
| is_claim_supported | `False` | OK |
| freshness | `RELIABLE` | OK |

### G - a required record that cannot be fetched, then a retry

| | | |
|---|---|---|
| submission | `sub-cold-gone-5a464a-4437` | OK |
| verdict | `EVIDENCE_UNAVAILABLE` | OK |
| status | `PENDING` | OK |
| evidence status | `EVIDENCE_UNAVAILABLE` | OK |
| records present | `False` | OK |
| records consistent | `False` | OK |
| source authenticity verified | `False` | OK |
| required event supported | `False` | OK |
| identity state | `UNKNOWN` | OK |
| condition state | `UNREADABLE` | OK |
| authenticity state | `SOURCE_UNVERIFIED` | OK |
| directed text hits | `0` | OK |
| is_claim_supported | `False` | OK |
| freshness | `UNKNOWN` | OK |

This submission was retried after its first round, so what the contract holds now is a fresh `PENDING` round. The first round settled as `EVIDENCE_UNAVAILABLE` (`RETRYABLE`, panel SKIPPED); its resolve transaction is listed above.

## The contract's own counters

| | |
|---|---|
| policies | 14 |
| challenges | 14 |
| submissions | 14 |
| resolved | 8 |

Only a settled verdict - `CLAIM_SUPPORTED` or `CLAIM_NOT_ESTABLISHED` - moves the resolved counter, which is why it is lower than the number of submissions.

## What this proves

- the deployed contract is the committed source, byte for byte;
- every record a verdict rests on still publishes the exact bytes its hash names;
- a cold chain that held its range is adjudicated as supported, and one with an excursion is not - the range comparison and the excursion arithmetic are code, and no model is told the range;
- checkpoints evidenced out of order do not establish a custody claim, because the order is decided from the instants the records state;
- records that disagree about which lot they describe produce `INCONSISTENT_EVIDENCE`, which is a finding about the records and not about the shipment;
- a record that instructs whoever reads it cannot produce a supported claim, and code - not the reading stage - is what caught it;
- a certificate not served from the host its issuer is registered to publish from leaves the source unverified, and the contract never claims a signature was checked;
- a required record nobody can fetch is `EVIDENCE_UNAVAILABLE` and retryable, never a finding about the world;
- every reliance gate is false for everything uncertain.

Schema `trustroute/1`, contract version `0.1.0`. 51 reads.

