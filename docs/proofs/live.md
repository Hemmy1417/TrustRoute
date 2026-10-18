# Live evidence

Written by `python scripts/verify.py`, which reads everything below off GenLayer Studionet. Nothing here is a transcript: re-run it and the network answers again. It needs no key, no funds and no GenLayer account.

| | |
|---|---|
| Network | GenLayer Studionet, chain 61999 |
| RPC | `https://studio.genlayer.com/api` |
| Contract | [`0xB70040Bca306122b795F7Cd9d7623aCe9175067B`](https://explorer-studio.genlayer.com/address/0xB70040Bca306122b795F7Cd9d7623aCe9175067B) |
| Deployer | `0x49AeDD95A65bE1DEa73628a5f90C52A06031b377` |
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
| deploy | [`0xfb6e29ca7ba74397...`](https://explorer-studio.genlayer.com/tx/0xfb6e29ca7ba7439701c147b25575282abb32fa91d243274b09751c4ad364d134) | FINALIZED | SUCCESS | 3 agree, 0 disagree, 2 idle of 5 |
| register pol-cold-ok-5a464a | [`0x6d0e9ee539bfa80d...`](https://explorer-studio.genlayer.com/tx/0x6d0e9ee539bfa80db98968462e0fb1946901deccf134a6f35eab810c80bb5a4d) | FINALIZED | SUCCESS | 5 agree, 0 disagree, 0 idle of 5 |
| publish pol-cold-ok-5a464a | [`0xf4bc4ae370ee18ba...`](https://explorer-studio.genlayer.com/tx/0xf4bc4ae370ee18bacae8c67854a87a70939415efea03115f6c2d14a6183fa0df) | FINALIZED | SUCCESS | 3 agree, 0 disagree, 2 idle of 5 |
| open chal-cold-ok-5a464a | [`0x8884196d45327e75...`](https://explorer-studio.genlayer.com/tx/0x8884196d45327e7557ea4cd0b0179a62caffccd694ed4dd8577819b02eb4bdeb) | FINALIZED | SUCCESS | 5 agree, 0 disagree, 0 idle of 5 |
| submit sub-cold-ok | [`0x9232172341d47174...`](https://explorer-studio.genlayer.com/tx/0x9232172341d47174df01692d2ce34e0dc65e0e0ff55331e10d53abfcfb7cf71e) | FINALIZED | SUCCESS | 3 agree, 0 disagree, 2 idle of 5 |
| resolve sub-cold-ok | [`0x564c1bb1da32f314...`](https://explorer-studio.genlayer.com/tx/0x564c1bb1da32f314f5db694b72396f5591af914335e1acac04be0f10236c2b4d) | FINALIZED | SUCCESS | 3 agree, 0 disagree, 2 idle of 5 |
| register pol-cold-exc-5a464a | [`0x329de72e3d07f9dc...`](https://explorer-studio.genlayer.com/tx/0x329de72e3d07f9dcbef683ebd21af31053dc70a81f16df6e40f4ac22f0e1d4a5) | FINALIZED | SUCCESS | 5 agree, 0 disagree, 0 idle of 5 |
| publish pol-cold-exc-5a464a | [`0xf3bb15315fae0b88...`](https://explorer-studio.genlayer.com/tx/0xf3bb15315fae0b887e36f332879a716c362b1ea8b21e8bb66a8a0cad033e276c) | FINALIZED | SUCCESS | 5 agree, 0 disagree, 0 idle of 5 |
| open chal-cold-exc-5a464a | [`0x0d69421784a34b3f...`](https://explorer-studio.genlayer.com/tx/0x0d69421784a34b3f885b0ecaf7152fbc267a4836cf54ed8431838ebccac56a41) | FINALIZED | SUCCESS | 5 agree, 0 disagree, 0 idle of 5 |
| submit sub-cold-exc | [`0x9af49d4850d11ed6...`](https://explorer-studio.genlayer.com/tx/0x9af49d4850d11ed64f0465436bdf16e22342a1a235962812df7ddfe07de88ef8) | FINALIZED | SUCCESS | 3 agree, 0 disagree, 2 idle of 5 |
| resolve sub-cold-exc | [`0x7eccd4041f025c8d...`](https://explorer-studio.genlayer.com/tx/0x7eccd4041f025c8dd01f86647133122241167eab1a5864d945576bb44e0344e7) | FINALIZED | SUCCESS | 3 agree, 0 disagree, 2 idle of 5 |
| register pol-cust-ooo-5a464a | [`0xb872566517ca6fbe...`](https://explorer-studio.genlayer.com/tx/0xb872566517ca6fbe71abe123843a1e482e3dfb498f2b249e7cb4cfece9be35e7) | FINALIZED | SUCCESS | 3 agree, 0 disagree, 2 idle of 5 |
| publish pol-cust-ooo-5a464a | [`0x2ca624141c3baec9...`](https://explorer-studio.genlayer.com/tx/0x2ca624141c3baec9c4532f02b8aec33d5b6ef5e1ec289fe85364ff1f5b63f21b) | FINALIZED | SUCCESS | 5 agree, 0 disagree, 0 idle of 5 |
| open chal-cust-ooo-5a464a | [`0x28424474ea916ee4...`](https://explorer-studio.genlayer.com/tx/0x28424474ea916ee466420e5799dacf39a1b134a728ef61df382eccdde4a49a11) | FINALIZED | SUCCESS | 5 agree, 0 disagree, 0 idle of 5 |
| submit sub-cust-ooo | [`0x6ba16b1b8e1f322a...`](https://explorer-studio.genlayer.com/tx/0x6ba16b1b8e1f322a8266a105bc775aa9dc7744a62cc00c1696bdfce2022ef99c) | FINALIZED | SUCCESS | 5 agree, 0 disagree, 0 idle of 5 |
| resolve sub-cust-ooo | [`0x4d5a9e7c3b3a2bc7...`](https://explorer-studio.genlayer.com/tx/0x4d5a9e7c3b3a2bc74eaf817819fd8abd3868a9d116b2a0d46eb89288d8b223bd) | FINALIZED | SUCCESS | 3 agree, 0 disagree, 2 idle of 5 |
| register pol-cust-conf-5a464a | [`0x7168f23b173b8003...`](https://explorer-studio.genlayer.com/tx/0x7168f23b173b8003aa271ddaaa8a774fa08071b0d5caa27482c769bc4511dde1) | FINALIZED | SUCCESS | 5 agree, 0 disagree, 0 idle of 5 |
| publish pol-cust-conf-5a464a | [`0xe3a609b04545f456...`](https://explorer-studio.genlayer.com/tx/0xe3a609b04545f45691823f7fc240ccb612e5d26eaeff57bff23ed09993ae5dcd) | FINALIZED | SUCCESS | 5 agree, 0 disagree, 0 idle of 5 |
| open chal-cust-conf-5a464a | [`0xfdc004b527dad869...`](https://explorer-studio.genlayer.com/tx/0xfdc004b527dad869d6fcb94b99f417f26d7bb4d4c30ae7c70e28bc7523ac8d44) | FINALIZED | SUCCESS | 3 agree, 0 disagree, 2 idle of 5 |
| submit sub-cust-conf | [`0xac8e98fed938fa8b...`](https://explorer-studio.genlayer.com/tx/0xac8e98fed938fa8bd06934be71057451647a04b81308941e849b0bc4f515c91a) | FINALIZED | SUCCESS | 3 agree, 0 disagree, 2 idle of 5 |
| resolve sub-cust-conf | [`0x5802ce8312e6eeb0...`](https://explorer-studio.genlayer.com/tx/0x5802ce8312e6eeb017d80e2c14b177b2f82a8c04fc2ca8197d63d821f0fab957) | FINALIZED | SUCCESS | 3 agree, 0 disagree, 2 idle of 5 |
| register pol-cust-dir-5a464a | [`0x4ee0a2ea0c959ba8...`](https://explorer-studio.genlayer.com/tx/0x4ee0a2ea0c959ba8b585b58b2580a1a6d5bc54ff4399f6cdfd9723fc140f2620) | FINALIZED | SUCCESS | 3 agree, 0 disagree, 2 idle of 5 |
| publish pol-cust-dir-5a464a | [`0xf77e2a47798e59c0...`](https://explorer-studio.genlayer.com/tx/0xf77e2a47798e59c09250f9248305ddbff1d4ef7f459317607a3824e264b0fb4e) | FINALIZED | SUCCESS | 5 agree, 0 disagree, 0 idle of 5 |
| open chal-cust-dir-5a464a | [`0xb2a04d6e67f0ab83...`](https://explorer-studio.genlayer.com/tx/0xb2a04d6e67f0ab83eb233364d8341c63ee022228cf73f180ea515e1018fcdb6f) | FINALIZED | SUCCESS | 5 agree, 0 disagree, 0 idle of 5 |
| submit sub-cust-dir | [`0xee6c9ef825bc6bb3...`](https://explorer-studio.genlayer.com/tx/0xee6c9ef825bc6bb3cf1637e0174396cc91da48317c1d209850b233386880a12b) | FINALIZED | SUCCESS | 5 agree, 0 disagree, 0 idle of 5 |
| resolve sub-cust-dir | [`0x49b21d93509be90e...`](https://explorer-studio.genlayer.com/tx/0x49b21d93509be90e2592d9b5275d8eb77d07ad2560de5998e121bc011e3dfd2e) | FINALIZED | SUCCESS | 3 agree, 0 disagree, 2 idle of 5 |
| register pol-origin-5a464a | [`0x0be5396a387686be...`](https://explorer-studio.genlayer.com/tx/0x0be5396a387686be05eb212a3c8fd47ad2cc4fa7eb7c6fe2a499307dc4707abe) | FINALIZED | SUCCESS | 5 agree, 0 disagree, 0 idle of 5 |
| publish pol-origin-5a464a | [`0x73cc03a2418190ef...`](https://explorer-studio.genlayer.com/tx/0x73cc03a2418190efc5e6ab9f5343ace81bca9469d0284699a93588af87030512) | FINALIZED | SUCCESS | 3 agree, 0 disagree, 2 idle of 5 |
| open chal-origin-5a464a | [`0x707efac93209a30a...`](https://explorer-studio.genlayer.com/tx/0x707efac93209a30a2f8141638733244e0f5ea28c89b284b647227da2b764271c) | FINALIZED | SUCCESS | 5 agree, 0 disagree, 0 idle of 5 |
| submit sub-origin | [`0x19de165cbab7e96b...`](https://explorer-studio.genlayer.com/tx/0x19de165cbab7e96b9a15181b6d543210226a8e2515188a8c092403537eb89be8) | FINALIZED | SUCCESS | 5 agree, 0 disagree, 0 idle of 5 |
| resolve sub-origin | [`0xaa75324b89a36923...`](https://explorer-studio.genlayer.com/tx/0xaa75324b89a36923a57e105ec792ba4a850a0b1cfff6d8db14180d08a4086a97) | FINALIZED | SUCCESS | 3 agree, 0 disagree, 2 idle of 5 |
| register pol-cold-gone-5a464a | [`0x0dfb22001b3d2856...`](https://explorer-studio.genlayer.com/tx/0x0dfb22001b3d2856200a714dd5ff5475e385906b6238f3837b376bdcdca3e671) | FINALIZED | SUCCESS | 3 agree, 0 disagree, 2 idle of 5 |
| publish pol-cold-gone-5a464a | [`0x441590c21a1057db...`](https://explorer-studio.genlayer.com/tx/0x441590c21a1057db1585918bcf12bd1d5dbac4eddf5b134a3bc98a903a30ef7a) | FINALIZED | SUCCESS | 3 agree, 0 disagree, 2 idle of 5 |
| open chal-cold-gone-5a464a | [`0x808b25451b117829...`](https://explorer-studio.genlayer.com/tx/0x808b25451b117829b373980e6db5750043d1e9ce17f34551e04fa717c6cf98f5) | FINALIZED | SUCCESS | 3 agree, 0 disagree, 2 idle of 5 |
| submit sub-cold-gone | [`0xda226f7b35eb76f6...`](https://explorer-studio.genlayer.com/tx/0xda226f7b35eb76f6e657886d005c911a67b25b60bcb39bf7fff7f0c94631184f) | FINALIZED | SUCCESS | 5 agree, 0 disagree, 0 idle of 5 |
| resolve sub-cold-gone | [`0xc07d47c3b183d802...`](https://explorer-studio.genlayer.com/tx/0xc07d47c3b183d802a74a05a0999ea9ecaba23c6d62d1120920f2cb5b0a8487c6) | FINALIZED | SUCCESS | 3 agree, 0 disagree, 2 idle of 5 |
| retry sub-cold-gone | [`0xfc80b6680dfb3c39...`](https://explorer-studio.genlayer.com/tx/0xfc80b6680dfb3c3972617c4098a4965bf40c49d9f496c87c8fe6cc8f4de2b64d) | FINALIZED | SUCCESS | 5 agree, 0 disagree, 0 idle of 5 |

## What the contract stores

### A - a cold chain whose log holds the range across the window

| | | |
|---|---|---|
| submission | `sub-cold-ok-5a464a` | OK |
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
| submission | `sub-cold-exc-5a464a` | OK |
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
| submission | `sub-cust-ooo-5a464a` | OK |
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
| submission | `sub-cust-conf-5a464a` | OK |
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
| submission | `sub-cust-dir-5a464a` | OK |
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
| submission | `sub-origin-5a464a` | OK |
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
| submission | `sub-cold-gone-5a464a` | OK |
| verdict | `EVIDENCE_UNAVAILABLE` | OK |
| status | `PENDING` | **WRONG** |
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

## The contract's own counters

| | |
|---|---|
| policies | 7 |
| challenges | 7 |
| submissions | 7 |
| resolved | 4 |

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

Schema `trustroute/1`, contract version `0.1.0`. 52 reads.

