"""Clinical red-line document pending; refuse all unreviewed model outputs."""
configured=False
def review(text):
    from pet_vision import NotConfigured
    raise NotConfigured('分诊安全规则尚未配置，不能展示照片分析结果')
