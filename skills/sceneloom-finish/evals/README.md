# Test cases

Each case runs against a sandboxed sceneloom data folder (`SCENELOOM_HOME`), never the real
`output/`. The prompts say "the newest project": the sandbox holds exactly one project, built by
`/home/lam/Documents/projects/sceneloom/skill-evals/make_fixtures.py`. Which fixture a case needs:

| Fixture | State of its one project |
|---|---|
| `empty` | no project yet |
| `script` | script done (4 scenes, "Con mèo giữ ngọn hải đăng") |
| `clips` | script, pictures and clips done with the mock provider |
| `audio` | as `clips`, plus mock voices and music |
| `flux` | the real 10-scene FLUX demo "Chiếc Đèn Lồng Của Mai", fully made |

Cases and fixtures: script `writes-a-checked-one-minute-story` (empty), `edits-one-line-without-redrawing`
(audio); visuals `draws-then-looks-at-every-picture` (script), `catches-the-wrong-picture` (flux);
sound `reports-what-it-could-not-hear` (clips), `switches-to-a-male-voice` (audio);
finish `assembles-and-writes-honest-package` (audio).
