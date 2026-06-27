# Video pipeline — SDD progress ledger
Repo: /home/goodsmileduck/karakeep-video-pipeline  (BASE abcbe95)
Topology: CLEAN PORTABLE REFERENCE — one local docker-compose, all services, normal internet, NO proxy/SG.

- VB video-fetcher: complete (commits 5e1f898 + fix ae4102b, review clean, 8 tests pass)
- VC video-tagger: complete (05aa019 + fix b1c6c93, review clean, 9 tests)
- VD validate: complete (compose config OK, both images build+import, 17 unit tests pass, live Karakeep list/tag/note/asset shapes verified)
- VE validate (compose config + image build + unit tests): pending  (no live IG test — RU box can't reach IG)
- VF docs + final review: pending
