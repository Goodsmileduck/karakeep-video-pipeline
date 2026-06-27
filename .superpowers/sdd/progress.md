# Video pipeline — SDD progress ledger
Repo: /home/goodsmileduck/karakeep-video-pipeline  (BASE abcbe95)
Topology: CLEAN PORTABLE REFERENCE — one local docker-compose, all services, normal internet, NO proxy/SG.

- VB video-fetcher: complete (commits 5e1f898 + fix ae4102b, review clean, 8 tests pass)
- VC video-tagger: in progress
- VD consolidated docker-compose.yml + .env.example: pending
- VE validate (compose config + image build + unit tests): pending  (no live IG test — RU box can't reach IG)
- VF docs + final review: pending
