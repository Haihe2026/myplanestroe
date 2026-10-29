# 自动匿名试用后台0.3.0

主Key仅服务器provider.env。公共领取由IMAGE_PUBLIC_TRIAL_ENABLED=yes与独立IMAGE_TRIAL_HMAC_KEY启用。IMAGE_TRIAL_IP_DAILY_LIMIT默认3，IMAGE_PILOT_MAX_IMAGES当前20。

POST /register接受43字符随机本机身份与accepted=true，事务内新赠5后台单位、前端显示5000；已有身份恢复原账户而不赠送。预算准入预留所有未用余额，不超总池。仅信任127.0.0.1代理提供的X-Real-IP；nginx需覆盖该头，不使用用户自报IP。

旧数据库保留并增建领取表；部署脚本备份DB、保留主Key和原账户。会话7天，原身份可续期。实际生图成功扣1后台单位，pending占用同一单位。此前旧邀请码接口仅作兼容，不是新用户入口。

发布构建用上级build_auto_trial_release.py，禁止覆盖历史包。发布与宿主验证由用户另行执行。
