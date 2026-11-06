"""证件照换底助手：固定话术。宿主原样转述，不改写。"""

SKILL_NAME = '证件照换底助手'

WELCOME = '欢迎使用WorkBuddy官方认证技能 ' + SKILL_NAME + '。'
CLOSE_WITH_NEED = '这个方向可以吗？'
CLOSE_OPEN = '你想从哪个方向开始？'
DEMO_INTRO = '都是效果示例图，不是你的真实结果。'
DEMO_UNAVAILABLE = '这次暂时没能展示示例图。'
PRICE_ANSWER = '按张计费，档位和金额在充值页上，确认方案后我带你过去。'

REASSURE_SAVED = '你确认的方案已经存好了，不用重新描述。'
REASSURE_FREE = '到这一步为止，没有产生任何扣费。'
CROSS_SKILL = '已经在其他技能开通过账户？同一账户的通用次数在已接入的技能间共享，这里不用重新付费。'
DECLINE = '没问题。等你需要图片的时候随时叫我。'
ONE_CHANGE = '想改的地方请每次只说一件事，一句话里有多个修改时，我会拆成几次依次完成。'
NO_REPEAT = '等待期间请不要重复发起，也不要换个说法重新提交，重复提交可能会重复计费。'
ORIGINAL_KEPT = '你发来的原照片没有改动，结果另存为新文件。'


def _reassure():
    return [REASSURE_SAVED, REASSURE_FREE]


def first_turn_close(has_need):
    """首轮收尾：不含链接、账户、价格。"""
    return CLOSE_WITH_NEED if has_need else CLOSE_OPEN


def confirm_paid(summary, wait_text):
    """方案与付费确认：只有用户明确肯定回答后才能继续。"""
    return '\n'.join([
        '我按这个方案做：' + summary + '。',
        '预计等待' + wait_text + '。AI处理的结果可能与原照片有细微差异；最终能否通过，以报名或发证机构的要求为准。',
        '开始前需要你确认两件事：',
        '1. 同意把这张照片发送去处理，只用于本次换底；',
        '2. 同意按张计费开始制作，费用以充值页和本次服务记录为准。',
        '两件都同意的话，回复「确认开始」。',
    ])


def auth(url, expires_hint='几分钟'):
    return '\n'.join([
        '我这边已经把你确认的换底方案存好了。首次出图需要先完成一次授权，授权本身不扣费。',
        '',
        '### 现在需要你做的',
        '1. 点开授权链接：[打开授权页](' + url + ')',
        '2. 按页面提示完成确认，不用手机号、不用验证码、不用 API Key。',
        '3. 链接' + expires_hint + '内有效；页面打不开或链接过期了，跟我说一声「重新取链接」，方案不受影响。',
        '',
        '做完跟我说一声「好了」，我接着按你确认的方案换底。',
        CROSS_SKILL,
    ] + _reassure())


def auth_short(url):
    return '\n'.join([
        '新的授权链接：[打开授权页](' + url + ')',
        '页面打不开就再跟我说一声，我重新取一个。',
    ] + _reassure())


def auth_pending():
    return '\n'.join([
        '我刚查了一次，还没看到授权完成。',
        '',
        '### 现在需要你做的',
        '1. 如果页面还开着，请在页面上完成确认。',
        '2. 页面打不开或已经过期，跟我说「重新取链接」。',
        '',
        '做完说一声「好了」，我再查一次，然后按你确认的方案继续。',
    ] + _reassure())


def final_step(url):
    return '\n'.join([
        '账户已经关联好了，你确认的方案也存着。',
        '只剩最后一步：选个套餐补充余额，选完我立刻按你确认的方案出图。',
        '',
        '### 现在需要你做的',
        '1. 打开充值页：[打开充值页](' + url + ')',
        '2. 档位和金额都在页面上，按需选择。',
        '3. 页面打不开或链接过期了，跟我说「重新取充值链接」。',
        '',
        '付款到账后跟我说「继续」，方案不用重说，我接着做。',
    ] + _reassure())


def topup_ask():
    """任务中途余额不足：先问，同意后才取链接。"""
    return '\n'.join([
        '这张还没有开始生成，这次没有扣次数，任务已经保留。',
        '当前余额不够做这一张。要我打开充值页吗？',
    ] + _reassure())


def topup_link(url):
    return '\n'.join([
        '充值页在这里：[打开充值页](' + url + ')',
        '页面打开不等于已经下单，充不充、充多少都由你决定。',
        '页面打不开或过期了，跟我说「重新取充值链接」。付款到账后说「继续」，我按原方案接着做。',
    ])


def payment_registered():
    return '已收到你的付款登记。到账以系统核实后的次数为准，稍等一下说一声「继续」我再查一次。图片需求已保留，到账就接着做。'


def credits_not_yet():
    return '我刚查了一次，次数还没到账。图片需求已保留，稍等一下再说「继续」，我再查。'


def start_recap(background, target, count=1):
    target_text = '，另存一份' + target + '像素' if target else ''
    return '开始制作：把照片背景换成' + background + target_text + '，共' + str(count) + '张，人物五官、发型和衣着尽量保持原样。' + NO_REPEAT


def delivery(paths, remaining, first_time, target_note=''):
    lines = ['做好了：']
    for p in paths:
        lines.append('- [' + p.rsplit('/', 1)[-1] + '](' + p + ')')
    lines.append('这次只替换了背景并清理了发丝边缘，人物五官、发型和衣着尽量保持原样；AI处理可能有细微差异，请放大检查边缘。')
    if target_note:
        lines.append(target_note)
    lines.append(ORIGINAL_KEPT)
    if remaining is None:
        lines.append('本次费用以服务记录为准。')
    else:
        lines.append('本次费用以服务记录为准，剩余 ' + str(remaining) + ' 次。')
    if first_time:
        lines.append('想调整直接说，比如「底色再浅一点」「换成蓝底」「另存一份 295×413」。' + ONE_CHANGE + '需要重新生成的调整可能再次按张计费，我会先跟你确认。')
    return '\n'.join(lines)


def size_mismatch(actual, requested):
    return '这次实际出图尺寸是 ' + actual + '，不是 ' + requested + '。我可以在本地按你的规格裁切另存一份。'


def crop_note(target):
    return '已按 ' + target + ' 像素在本地居中裁切另存一份，并重新打开核对过尺寸；头部位置如需上下移动，跟我说一声。'


def failure(reason_kind, charge_kind):
    reason = {
        'busy': '服务正在处理较多请求',
        'network': '网络连不上',
        'rejected': '这张照片暂时无法按这个要求处理',
        'input': '照片文件不符合要求',
    }[reason_kind]
    charge = {
        'not_started': '这次还没有开始生成，没有扣次数。',
        'record': '费用以服务记录为准。',
    }[charge_kind]
    return '这次没有拿到图——' + reason + '。' + charge + '稍后想再试，直接告诉我「重新生成」。'


def busy_kept():
    return '这次没有拿到图——服务正在处理较多请求。这次还没有开始生成，没有扣次数，任务已保留。稍后说「继续」，我按原方案接着做。'


def still_processing():
    return '还在处理中，任务已保留。稍后说「继续」，我接着查这一张，不会重新提交。' + NO_REPEAT


def progress_unknown():
    return '当前进度未能确认，费用以服务记录为准。任务已保留，稍后说「继续」，我接着查这一张，请不要重复生成。'


def download_incomplete():
    return '图片下载暂时未完成，费用以服务记录为准，请不要重复生成。稍后说「继续」，我再取一次这张图。'


def credentials_reset():
    return '登录状态已过期，我已清除旧的登录信息。' + REASSURE_SAVED + '接下来重新授权一次即可继续，授权本身不扣费。'


def account_summary(remaining):
    return '\n'.join([
        '剩余可用次数：' + str(remaining) + ' 次',
        '这里目前只能查看剩余次数；需要补充次数时，回复「充值」我为你打开充值页。',
    ])


def account_missing():
    return '这台设备上还没有关联账户。确认好换底方案后，我会带你完成一次授权，授权本身不扣费。'


def feedback_unavailable():
    return '谢谢你的反馈，我已经整理好了你的原话。这里暂时不能直接提交反馈单，后续会尽快开放。'


def input_error(filename, problem):
    return '照片「' + filename + '」' + problem + '，这次没有发送，也没有扣次数。换一张清晰的 PNG 或 JPG 照片发我就行。'


def refuse_misuse():
    return '这个需求我不能处理：本技能只处理你本人或已获授权的照片，不做伪造证件、冒用他人肖像，也不改五官、发型和衣着。'


def favorite_done():
    return '已收藏，以后问证件照换底问题会优先由' + SKILL_NAME + '接待。想取消时说「取消收藏' + SKILL_NAME + '」即可。'


def favorite_unsupported():
    return '当前环境暂不支持收藏技能。'
