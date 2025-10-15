# Domain RAG MVP ? User Guide

����README�́u�����悤�ɂ��̃T�C�g���g����v���߂̎菇�ɓ������Ă��܂��B�݌v�E�d�l�̏ڍׂ� `docs/specification.md` ���Q�Ƃ��Ă��������B

�ړI
- ���{���pdf���i���b�W�ɂ��A���{��̎���Ɏ����񓚂��܂��iJP��JA�񓚁j�B

�O��
- Docker/Docker Compose �����p�ł���
- OpenAI API�L�[������i`.env.local` �ɐݒ�j

�Z�b�g�A�b�v�i�ŒZ5���j
1) �i���b�W��u��
- `llm/` �z���� `.pdf`��������`.txt`�A`.md`��u��

2) API�L�[��ݒ�
- `.env.local` ���쐬���A�ȉ����L��
```
OPENAI_API_KEY=sk-...
```

3) �ݒ���m�F�i�C�Ӂj
- `config/settings.yml`�i����l�̂܂܂ł�����j
```
threshold: 0.50
top_k: 5
google_form_url: "https://example.com/form"
translate_query: true
doc_lang: "en"
answer_lang: "ja"
```

4) �R���e�i���r���h
- `docker compose build`

5) �������쐬�i����/�X�V���j
- `docker compose run --rm indexer`
- �`�����N�m�F�i�C�Ӂj: `docker compose run --rm indexer python scripts/build_index.py --input /app/llm --out /app/artifacts --peek 8`

6) API���N��
- `docker compose up -d api`
- �w���X: `curl http://127.0.0.1:8000/healthz`�i`{"ok": true}` �Ȃ�OK�j

7) Web�T�C�g���g��
- �u���E�U�� `http://127.0.0.1:8000/`
- �������͂��đ��M�B�Y�����ア�ꍇ�́u���₢���킹�v�{�^�����\������܂��B

�X�V�t���[�i�i���b�W���C��/�ǉ�������j
1) `llm/` �� `.md/.txt` ���X�V
2) �����쐬���Ď��s: `docker compose run --rm indexer`
3) API�ċN��: `docker compose restart api`

�g���u���V���[�g
- ��� `fallback: true`
  - �i���b�W���Ɋ��Ҍ�b�������^�������e���^臒l�������\��
  - �΍�: `--peek` �Ń`�����N���m�F�A`threshold` �� 0.30?0.50 �Œ����A`top_k` �� 3��5��
- `/healthz` �� `ok:false`
  - API�L�[���ݒ�A�܂��͍������쐬
  - �΍�: `.env.local` ���m�F�A�菇5�����s
- Compose�̌x���iversion obsolete�j
  - �{���|�� `version:` ���폜�ς݁B�x�����o��ꍇ��Compose�̃o�[�W�������m�F

�Q�l�i�C�Ӂj
- ����e�X�g���܂Ƃ߂Ď��s: 
  - `docker compose exec api python scripts/run_acceptance_tests.py --file /app/docs/acceptance_test.yml --base-url http://127.0.0.1:8000`
- �d�l�E�J���菇: `docs/specification.md`, `docs/dev_steps.md`

