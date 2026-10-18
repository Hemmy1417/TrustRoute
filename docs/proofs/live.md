# Live evidence

Written by `python scripts/verify.py`, which reads everything below off GenLayer Studionet. Nothing here is a transcript: re-run it and the network answers again. It needs no key, no funds and no GenLayer account.

| | |
|---|---|
| Network | GenLayer Studionet, chain 61999 |
| RPC | `https://studio.genlayer.com/api` |
| Contract | [`0xf2Fc34063eab9Ca8f531fEb5A5BbAd81Bb450150`](https://explorer-studio.genlayer.com/address/0xf2Fc34063eab9Ca8f531fEb5A5BbAd81Bb450150) |
| Deployer | `0x3d642eD4d279494b4ee7ef0Fa81A322400fe467d` |
| Source commit | `471b56b` |
| Contract source | `contracts/trustroute.py`, 136826 bytes, sha256 `8088723dc96fbaf8937b8de15a80318e997a10aea9d23acc254765d7bac9d783` |
| Deployed bytes | 136826 bytes, sha256 `8088723dc96fbaf8937b8de15a80318e997a10aea9d23acc254765d7bac9d783` |
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
| deploy | [`0x9729f8d74b3242d9...`](https://explorer-studio.genlayer.com/tx/0x9729f8d74b3242d929ed0dfe72c096440a7f5027f4f9f6b4cc556b68f0acdf96) | FINALIZED | SUCCESS | 3 agree, 0 disagree, 2 idle of 5 |
| register pol-cold-ok-471b56-5c6c | [`0xc98bec9ad44bb240...`](https://explorer-studio.genlayer.com/tx/0xc98bec9ad44bb240689cabf615d3f2f78d2052cf57728a09c92ee1d6c3c7e6f3) | FINALIZED | SUCCESS | 5 agree, 0 disagree, 0 idle of 5 |
| publish pol-cold-ok-471b56-5c6c | [`0x94f72332835a77df...`](https://explorer-studio.genlayer.com/tx/0x94f72332835a77df22c25da5352513ccfd58b1ba1eec77082ae6a8235509f1ce) | FINALIZED | SUCCESS | 3 agree, 0 disagree, 2 idle of 5 |
| open chal-cold-ok-471b56-5c6c | [`0x79438ed5990984d8...`](https://explorer-studio.genlayer.com/tx/0x79438ed5990984d8b1becc95d41dbc699a93866867f7ba98403f8c866342f007) | FINALIZED | SUCCESS | 5 agree, 0 disagree, 0 idle of 5 |
| submit sub-cold-ok | [`0x2817c3b570343e30...`](https://explorer-studio.genlayer.com/tx/0x2817c3b570343e30e04bf691ce6850d16b2d6db2656982ac925f90b46c9d2a41) | FINALIZED | SUCCESS | 5 agree, 0 disagree, 0 idle of 5 |
| resolve sub-cold-ok | [`0xf9e04e2725ab2593...`](https://explorer-studio.genlayer.com/tx/0xf9e04e2725ab2593dd36ba6467fb565fdbe51acac35e1b32d9c4003c961c1cfd) | FINALIZED | SUCCESS | 3 agree, 1 disagree, 1 idle of 5 |
| register pol-cold-exc-471b56-5c6c | [`0x7ace48112d390ad8...`](https://explorer-studio.genlayer.com/tx/0x7ace48112d390ad8d54c22814410fc5eb8ee5e9748472d1e9b52f45552220016) | FINALIZED | SUCCESS | 3 agree, 0 disagree, 2 idle of 5 |
| publish pol-cold-exc-471b56-5c6c | [`0x4e3389b7b707f3a6...`](https://explorer-studio.genlayer.com/tx/0x4e3389b7b707f3a6ee8868a98ec8b8f8d11173c738f31b58129de685a8e90eb3) | FINALIZED | SUCCESS | 5 agree, 0 disagree, 0 idle of 5 |
| open chal-cold-exc-471b56-5c6c | [`0xb6983f55ec51dfd3...`](https://explorer-studio.genlayer.com/tx/0xb6983f55ec51dfd330c5b06b122229125a4189cb7d3398f95567f04cdd7bdc1d) | FINALIZED | SUCCESS | 5 agree, 0 disagree, 0 idle of 5 |
| submit sub-cold-exc | [`0x2b3332015aba3bf9...`](https://explorer-studio.genlayer.com/tx/0x2b3332015aba3bf9773132bfe662565c4867652ef929f1441cc7c81611e0cf37) | FINALIZED | SUCCESS | 3 agree, 0 disagree, 2 idle of 5 |
| resolve sub-cold-exc | [`0xcf4db5d57e10cbe3...`](https://explorer-studio.genlayer.com/tx/0xcf4db5d57e10cbe360871245e87bb73670c55165c3827297c58f61cbbb1ec8fa) | FINALIZED | SUCCESS | 3 agree, 0 disagree, 2 idle of 5 |
| register pol-cust-ooo-471b56-5c6c | [`0xa6f9d1caf3aa8685...`](https://explorer-studio.genlayer.com/tx/0xa6f9d1caf3aa86853ec2722852eb3bbd50ef46685dc701d328ca7c841a14693f) | FINALIZED | SUCCESS | 3 agree, 0 disagree, 2 idle of 5 |
| publish pol-cust-ooo-471b56-5c6c | [`0xdb20d956b563ac77...`](https://explorer-studio.genlayer.com/tx/0xdb20d956b563ac77530fa484d321505e3b07939abd8d8edaa01d915ba61d1ff9) | FINALIZED | SUCCESS | 3 agree, 0 disagree, 2 idle of 5 |
| open chal-cust-ooo-471b56-5c6c | [`0xa778aca1f255f1bb...`](https://explorer-studio.genlayer.com/tx/0xa778aca1f255f1bb536e73e31e63617cfd4f0ae850ed1bb6cd2ce1e836b400be) | FINALIZED | SUCCESS | 3 agree, 0 disagree, 2 idle of 5 |
| submit sub-cust-ooo | [`0xec4a024566d90347...`](https://explorer-studio.genlayer.com/tx/0xec4a024566d9034730734685d6ac8c3ba04ea32377be96dd155bef7decd83546) | FINALIZED | SUCCESS | 5 agree, 0 disagree, 0 idle of 5 |
| resolve sub-cust-ooo | [`0xa43fc06c0c5a3a3f...`](https://explorer-studio.genlayer.com/tx/0xa43fc06c0c5a3a3f2d63351f7dec2221cbaa294f7f7c07727fb9e600d1dd31e4) | FINALIZED | SUCCESS | 3 agree, 0 disagree, 2 idle of 5 |
| register pol-cust-conf-471b56-5c6c | [`0xbfabc35b62355c5b...`](https://explorer-studio.genlayer.com/tx/0xbfabc35b62355c5b53bdaaeb1598d605261ec2c2ebed1d127f9512fb43a2a341) | FINALIZED | SUCCESS | 3 agree, 0 disagree, 2 idle of 5 |
| publish pol-cust-conf-471b56-5c6c | [`0x5a60e195867dcb7e...`](https://explorer-studio.genlayer.com/tx/0x5a60e195867dcb7e8d3410d7db16c5565026d3997c7f9967edc3d93a6db0a3ec) | FINALIZED | SUCCESS | 5 agree, 0 disagree, 0 idle of 5 |
| open chal-cust-conf-471b56-5c6c | [`0xfc01e10f08f7b64e...`](https://explorer-studio.genlayer.com/tx/0xfc01e10f08f7b64e224a2b68002a8c545f87c0ae9f6a14dc23255f63512649e3) | FINALIZED | SUCCESS | 5 agree, 0 disagree, 0 idle of 5 |
| submit sub-cust-conf | [`0xb77e399628175143...`](https://explorer-studio.genlayer.com/tx/0xb77e3996281751435416955bcf30d2b8bc5032ba26add4e479b155bf3d72fcc2) | FINALIZED | SUCCESS | 3 agree, 0 disagree, 2 idle of 5 |
| resolve sub-cust-conf | [`0x9e7010ed0ab70d84...`](https://explorer-studio.genlayer.com/tx/0x9e7010ed0ab70d8498e07602539bc4c92b694e7b7184711dae44372baa42b87d) | FINALIZED | SUCCESS | 3 agree, 0 disagree, 2 idle of 5 |
| register pol-cust-dir-471b56-5c6c | [`0xb61169f7e708891e...`](https://explorer-studio.genlayer.com/tx/0xb61169f7e708891e7c9e61fbce5201b057da2c5035de61b27b931556a8919446) | FINALIZED | SUCCESS | 3 agree, 0 disagree, 2 idle of 5 |
| publish pol-cust-dir-471b56-5c6c | [`0x32f7f1e12c5510c6...`](https://explorer-studio.genlayer.com/tx/0x32f7f1e12c5510c62d0eb00694d0cc548a4788986efcd874e2ff600408bba356) | FINALIZED | SUCCESS | 3 agree, 0 disagree, 2 idle of 5 |
| open chal-cust-dir-471b56-5c6c | [`0xe35e63022b53dcb8...`](https://explorer-studio.genlayer.com/tx/0xe35e63022b53dcb8aff819bfd55fadda38fd85f0b6672ac60506ac6385881079) | FINALIZED | SUCCESS | 3 agree, 0 disagree, 2 idle of 5 |
| submit sub-cust-dir | [`0x52f185835294202d...`](https://explorer-studio.genlayer.com/tx/0x52f185835294202deb08784ff6099749faf542e0eb7d9ccf909f2bb55daa7a04) | FINALIZED | SUCCESS | 3 agree, 0 disagree, 2 idle of 5 |
| resolve sub-cust-dir | [`0xac45125f8a9638c6...`](https://explorer-studio.genlayer.com/tx/0xac45125f8a9638c62f7d2541b1edfa7e9e16b56394acf3ef0fae8cc4d1e9a947) | FINALIZED | SUCCESS | 3 agree, 0 disagree, 2 idle of 5 |
| register pol-origin-471b56-5c6c | [`0x9c7c895a913d7e83...`](https://explorer-studio.genlayer.com/tx/0x9c7c895a913d7e83fd2dc795d458eec62f5cd478d7b3baee5f77ece2bb021e4f) | FINALIZED | SUCCESS | 5 agree, 0 disagree, 0 idle of 5 |
| publish pol-origin-471b56-5c6c | [`0x818cab8406ff7783...`](https://explorer-studio.genlayer.com/tx/0x818cab8406ff77835d28e8f2d6b8007f3242a478de45d07f659ee888c6d492eb) | FINALIZED | SUCCESS | 3 agree, 0 disagree, 2 idle of 5 |
| open chal-origin-471b56-5c6c | [`0x5e803c1cccab38b7...`](https://explorer-studio.genlayer.com/tx/0x5e803c1cccab38b7000840b974390878440af019222968124e43ac2454592e05) | FINALIZED | SUCCESS | 3 agree, 0 disagree, 2 idle of 5 |
| submit sub-origin | [`0xf7701b519de9e836...`](https://explorer-studio.genlayer.com/tx/0xf7701b519de9e836ba8da159ddefef81b17c012f56de289e06e418040774d968) | FINALIZED | SUCCESS | 4 agree, 0 disagree, 1 idle of 5 |
| resolve sub-origin | [`0xbfbfc2efc0fb6b66...`](https://explorer-studio.genlayer.com/tx/0xbfbfc2efc0fb6b665fe846294411cf3737ec9ed762580ff61dec6e428a8bd23c) | FINALIZED | SUCCESS | 3 agree, 0 disagree, 2 idle of 5 |
| register pol-cold-gone-471b56-5c6c | [`0x708ae7822cddf7d6...`](https://explorer-studio.genlayer.com/tx/0x708ae7822cddf7d67a5056adfd368093934d514655e847a11027d4fc8e5024fb) | FINALIZED | SUCCESS | 5 agree, 0 disagree, 0 idle of 5 |
| publish pol-cold-gone-471b56-5c6c | [`0xa2d72967710e75dc...`](https://explorer-studio.genlayer.com/tx/0xa2d72967710e75dc9b5c6fb0942a0f496634b939910c6720ae4dbbca2ddd7781) | FINALIZED | SUCCESS | 3 agree, 0 disagree, 2 idle of 5 |
| open chal-cold-gone-471b56-5c6c | [`0x4869086aa378ea43...`](https://explorer-studio.genlayer.com/tx/0x4869086aa378ea43aec910a2cea9d6914b6860c9cefcab0b28d611aa4f80977b) | FINALIZED | SUCCESS | 5 agree, 0 disagree, 0 idle of 5 |
| submit sub-cold-gone | [`0x19cf69382b940343...`](https://explorer-studio.genlayer.com/tx/0x19cf69382b94034354a5c5cde4ec4e59f640d3760b27298f1e4fcf598cc91df0) | FINALIZED | SUCCESS | 3 agree, 0 disagree, 2 idle of 5 |
| resolve sub-cold-gone | [`0xf2cdad8f5092af45...`](https://explorer-studio.genlayer.com/tx/0xf2cdad8f5092af452bc5b633ce967b7c76359bef94f393ef4a9199ce9109409d) | FINALIZED | SUCCESS | 3 agree, 0 disagree, 2 idle of 5 |
| retry sub-cold-gone | [`0x68cd9734c09908ef...`](https://explorer-studio.genlayer.com/tx/0x68cd9734c09908efb340445754c7cc155a5206c4c02c03c00c40ba26e2606712) | FINALIZED | SUCCESS | 3 agree, 0 disagree, 2 idle of 5 |

## What the contract stores

### A - a cold chain whose log holds the range across the window

| | | |
|---|---|---|
| submission | `sub-cold-ok-471b56-5c6c` | OK |
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
| submission | `sub-cold-exc-471b56-5c6c` | OK |
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
| submission | `sub-cust-ooo-471b56-5c6c` | OK |
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
| submission | `sub-cust-conf-471b56-5c6c` | OK |
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
| submission | `sub-cust-dir-471b56-5c6c` | OK |
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
| submission | `sub-origin-471b56-5c6c` | OK |
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
| submission | `sub-cold-gone-471b56-5c6c` | OK |
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

