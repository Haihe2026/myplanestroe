# 给 Claude：银发写真照相馆 1.0.0 A3 未过，出 1.0.1

产品：银发写真照相馆，slug mps-silver-portrait-studio。
A3 报告：pipeline/products/mps-silver-portrait-studio/03-test-report.md（2026-11-12T10:04:02+08:00，Codex 独立检查，test_failed，rounds.test=1）。
固定包：mps-silver-portrait-studio-1.0.0.zip，2,603,008 字节、25 文件，SHA256 b06ce740ca094ee56dd9483c368599dc4ecbe2e4ff0f858f6fa7b258f3deb44c。
任务：修复下述一项缺陷，出 1.0.1（版本号大于 1.0.0），重跑隔离 A2（契约＋端到端），固定新 ZIP/SHA 后置 package_ready，再交 Codex 独立复查。1.0.0 不是可上传版，绝不上传 1.0.0。

## 本轮缺陷（出处：03-test-report.md）

### SLV-A3-01（P2）：改方案早退后仍可执行旧确认

- 现象：用照片 A 完成普通主题 plan 及三项 confirm，尚未发生成 POST；用户要求改为给妈妈代购照片 B，或改老兵主题，但新被摄本人许可/老兵条件未问清或明确不同意。宿主按 SKILL 第 2 节重新 plan 后早退，旧的三项同意和旧 idem 没作废；用户随后说“继续”，仍能提交旧图旧角色。
- 固定代码证据：scripts/studio.py:418–464 读旧草稿后，432–451 的资格/本人许可/老兵条件分支和 453–464 的脸部/文字/输入校验均可直接 emit 早退，没有持久作废旧确认；只有 465–469 成功 plan 才把三同意设 false、idem/job/body 摘要清空并 save。早退时新图路径即使内存改过也没有存盘，旧 A/角色/键继续留在磁盘。随后 resume 885–906 可转到 run 629–667：632 仅看旧三同意＋旧 idem，638 对旧图 A 构体；旧 A 有效时经账户/Key 流程可在 667 提交旧图旧角色方案。needs_credits 分支即使查到补充次数，也会恢复旧 confirmed 再 run。
- 修复：对尚未提交的 replan，应在进入可早退的新资格/新图验证路径前，先持久作废旧的执行确认和待提交键，清楚保留/标记待完善的新方案。只要新信息未齐、被拒绝或验证失败，run/resume/regenerate 不得借旧许可生成旧 A。修复细节由 Claude 实现，不改变既有收费、鉴权或后端。
- 红线（不得回退）：对已提交/submit_unknown/download_pending 或已有 job_id 的原任务继续优先只读续查，replan 仍拒绝，不清原键/原体/锁，不因本地图或新资格变化重建任务。正常新方案重新取得本人照片/具体文件传输/订购人计费三项明确同意后，才允许新键提交。
- A2 须补的回归（须能反证旧 1.0.0 的早退遗漏，不能只重复成功分支或放宽断言）：
  - 从旧 confirmed 和无 job_id 的 needs_credits 各起一组：新 family_proxy 许可 unknown/no、adult 未知/no、新老兵条件 unknown/active/not_veteran 或主题同意 no、改图 B 缺失/截断、脸不清/文字过长等早退；返回后重读持久状态，旧三同意与可执行键已失效。
  - 早退后重启/重读再 run 或 resume：只等待补齐/重新确认，生成 POST 0、扣次 0，不能发旧 A；regenerate 也不能绕过。区分匿名首次遥测与业务请求。
  - 新方案 B 信息齐全并重新明确三项同意后才提交新图/主题/代购关系，正常路径仍通。
  - 对 submit_unknown/submitted/download_pending/已有 job_id，replan 不清原键/原体/锁；即使本地图坏了仍只 GET 原任务、无第二次生成 POST。
  - 现有契约测试 698–724 的注释已写“含下单人或同意情况变化清待提交键和确认”，但只测 family_proxy+informed=yes 的成功 replan；新增用例应能反证旧 1.0.0 的早退遗漏。

## 前序产品缺陷全清单（修复不重犯：逐项复核未回退，F1）

- FAM-01（P1，全家福）：401 后误把 404 当重提许可产生第二次生成 POST。
- FAM-02（P1，全家福）：401 恢复失败后清原键、解除原任务保护。
- FAM-03（P2，全家福）：缺一张示例仍返回成功。
- TRV-01（P2，旅行）：绑定未确认仍生成；TRV-01-R1：绑定 401 旧 Key 不清致恢复循环（确定 401 清 Key 和绑定标记、保留原安装身份和原任务、下次沿原 install_secret 取新 Key 确认 bound=true）。
- TRV-02（P2，旅行）：坏输入仅验头（只验 PNG/JPEG 头）；TRV-02-R1：完整校验资源无界（PNG z.decompress 无 max_length；JPEG 重复 DHT 无界计算；要求 PNG 有限输出块＋扫描行预算硬上限、JPEG 延迟建表/复用/限累计工作量）。
- TRV-03（P2，旅行）：首次上报失败自动重试（发出前持久化 attempted、失败即弃）。
- TRV-04（P2，旅行）：特异服饰路由被词序覆盖（明确目的地优先、无目的地时和服→kyoto、汉服/唐风→xian）。
- TRV-05（P2，旅行）：传图告知未含接收方类别（告知图片服务及算力供应商类别、不披露品牌）。
- PAY-01：paid 全新环境不走关联入口给链接（须走一次性关联入口 POST /quick-entry 给链接）。
- PAY-02：expires_in=0 失效链接仍转述（须沿原安装身份重取一次、仍失效不转述）。
- PAY-03：description 末句未按 SOP 7.3.2 模板涵盖本技能账户问题。
- PAY-04：demo 触发遥测请求（须离线、不联网、不读凭证）。
- A3-E01：中英示例语义不对齐（各最多 3 条且数量一致、逐条同一场景）。
- A3-E02/A3-E03：示例图路径含空格/#（或空格编码 %20、# 编码 %23），回归须含带空格与带 # 的合成路径。
- MAT-A3-01（P1，孕妈）：description_en 未引用冒号致 YAML 解析失败（合法引用字符串或块标量；用真正 YAML 解析器查最终 ZIP 原始内容）。
- MAT-A3-02（P2，孕妈）：确认后坏图先发账户 HTTP（未提交分支先本地验图/SHA 再碰账户；未知/已提交不得因坏图/换图/换档新建任务或解除原锁）。
- MAT-A3-03（P2，孕妈）：未问成年将未知填 no 误拒（未知先补问，不走明确不符合分支；只在明确不符合时拒绝且反馈针对实际原因）。
- WED 前科（婚纱）：离线示例触发上报、确认后文件可替换、成品链接未编码。
- 斜杠案（全家福，已核查无此问题）：状态目录不以点开头、对外路径过 md_safe_path、demos.json 全裸文件名、包内有回归测试。

## 其他要求

- 保留所有通过项及 10 图/logo 原字节：10 张示例图（demo-assets/，每张 512×768）与主题 logo（02-package/dist/logo.png，512×512 PNG）原字节不动，不重新生成、不替换。
- 欢迎句逐字：「欢迎使用WorkBuddy官方认证技能 银发写真照相馆」。
- 付费：通用套餐 https://aistore.zhaopintong.com/membership/，0 次免费试用。
- 版本：1.0.1，frontmatter 与包内版本一致；SKILL.md ≤15KiB；目录最多两级；examples 中英各 ≤3 且数量一致。
- 脚本＋SKILL.md＋版本打包三部分都改到位，不只改一半；重跑隔离 A2 全过后固定新 ZIP/SHA 置 package_ready。
