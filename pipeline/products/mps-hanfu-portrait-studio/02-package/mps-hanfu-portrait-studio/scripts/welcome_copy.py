"""汉服写真照相馆：固定话术。宿主原样转述，不改写。"""

from urllib.parse import unquote

SKILL_NAME = '汉服写真照相馆'

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
SHAPE_NAMES = {'portrait': '竖版 2:3', 'landscape': '横版 3:2', 'square': '方图 1:1'}
LIKENESS = '会尽力保持照片里可见的五官、肤色和体态，发型按所选套系换成相应髻式，细节差异可能存在；AI 生成的效果可能与本人有差异，请以你自己看过满意为准。'
DISCLOSURE = 'AI 生成汉服写真，非实拍'


def _reassure():
    return [REASSURE_SAVED, REASSURE_FREE]


def first_turn_close(has_need):
    """首轮收尾：不含链接、账户、价格。"""
    return CLOSE_WITH_NEED if has_need else CLOSE_OPEN


def plan_summary(title, shape_name, size, outfit):
    return ('「' + title + '」汉服写真，你本人这张单人照，服饰与妆造：' + outfit + '（整套同一形制），' +
            shape_name + '（' + size.replace('x', '×') + '），1 张')


# 本次照片传输同意：告知接收方类别（不点名具体品牌或技术）
RECIPIENTS = '图片服务及算力供应商'
UPLOAD_CONSENT = '同意把这张照片发送给' + RECIPIENTS + '处理，只用于本次制作'
ART_NOTE = '这个主题是艺术风格写真，不是考古精确复原。'
HISTORY_NOTE = '服饰按这一朝代风格的参考方向来做，不代表考古精确复原。'


def confirm_paid(summary, wait_text, features, kind='history'):
    """方案与付费确认：只有用户明确肯定回答后才能继续。三项同意彼此独立，不能互相代替。"""
    lines = ['我按这个方案做：' + summary + '。']
    if features:
        lines.append('我会按确认过的样子保留人物：' + features + '。不对的话直接告诉我。')
    lines.append('成品是' + DISCLOSURE + '；' + (ART_NOTE if kind == 'art' else HISTORY_NOTE) +
                 '人脸和服饰细节可能有差异，不能当作证件或任何证明。')
    return '\n'.join(lines + [
        '预计等待' + wait_text + '。' + LIKENESS,
        '开始前需要确认三件事：',
        '1. 这张照片是你本人的单人照，你同意用它制作这次汉服写真；',
        '2. ' + UPLOAD_CONSENT + '；',
        '3. 同意按张计费开始制作，费用以充值页和本次服务记录为准。',
        '三件都同意的话，回复「确认开始」。付过款不能代替前两项同意。',
    ])


def not_eligible(reason='minor'):
    """明确说了不符合时才用；按实际原因反馈，不让用户换图去补自述。"""
    if reason == 'minor':
        return '汉服写真只为成年人本人制作，这次没法帮忙做。这次没有产生任何扣费。'
    return ('汉服写真只用你本人的单人照制作，这次先不制作，没有产生任何扣费。'
            '朋友也想拍的话，请对方用自己的单人照、自己来确认和制作；想做你自己的，发一张你本人的单人照就行。')


ELIGIBILITY_ASK = {
    'self': '照片里是你本人吗？',
    'adult': '你是成年人吗？',
}


def needs_eligibility(missing):
    """本人、成年还没确认：一次合并补问，只按自述，不看照片估计、不需要任何证明。"""
    asks = [ELIGIBILITY_ASK[k] for k in ('self', 'adult') if k in missing]
    return ('开始前还需要确认一下：' + ''.join(asks) +
            '按实际情况回答就行，不需要任何证明，我也不会看照片估计年龄。这次没有产生任何扣费。')


def form_invalid():
    return ('这个主题只能整套换成唐风、宋风或明风（园林主题另可选曲裾），不同朝代的衣服不混在一起穿。'
            '说一下想要哪一套就行，这次没有产生任何扣费。')


def people_unsupported():
    return ('汉服写真目前只做你本人一个人的单人照，这张照片里不止一个人，双人或多人合影这边做不了。'
            '朋友也想拍的话，请各自用本人的单人照分别来做、分别确认。这次没有产生任何扣费。')


def needs_clearer_photo():
    return '这张照片里脸看不太清，为了保住你的样子，这次先不制作，没有产生任何扣费。换一张脸部清楚、没有遮挡的本人单人照发我就行。'


def text_invalid():
    return '描述稍微长了点，用一两句短话说说就行（比如衣服颜色、戴不戴眼镜、想要什么配色）。'


def needs_photo():
    return '请发一张你本人的清晰单人照给我，我按选好的汉服主题来做。'


def task_locked():
    return '这一张还在处理中，任务已保留。稍后说「继续」，我接着查这一张，不会重新提交。' + NO_REPEAT


def auth(url, expires_hint='几分钟'):
    return '\n'.join([
        '我这边已经把你确认的汉服写真方案存好了。首次出图需要先完成一次授权，授权本身不扣费。',
        '',
        '### 现在需要你做的',
        '1. 点开授权链接：[打开授权页](' + url + ')',
        '2. 按页面提示完成确认，不用手机号、不用验证码，也不用填写任何密钥。',
        '3. 链接' + expires_hint + '内有效；页面打不开或链接过期了，跟我说一声「重新取链接」，方案不受影响。',
        '',
        '做完跟我说一声「好了」，我接着按你确认的方案制作。',
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
        '付款后即时到账，跟我说「继续」，方案不用重说，我接着做。',
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


def paid_confirmed(remaining):
    """只在查到可用次数后使用。"""
    return '我刚查了一次，账户剩余可用次数 ' + str(remaining) + ' 次。说一声「继续」，我按原方案接着做。'


def paid_not_yet(url=None):
    """用户说已付款但还没查到到账：如实说，不当作已到账。"""
    lines = ['我刚查了一次，还没看到这笔到账，没有扣任何次数。图片需求已保留，稍等一下再说「付好了」或「继续」，我再查。']
    if url:
        lines.append('还没付款的话，充值页在这里：[打开充值页](' + url + ')，页面打不开或过期了，跟我说「重新取充值链接」。')
    return '\n'.join(lines)


def credits_not_yet():
    return '我刚查了一次，还没看到这笔到账。图片需求已保留，稍等一下再说「继续」，我再查。'


def start_recap(title, outfit, shape_name, size, count=1):
    return ('开始制作：「' + title + '」汉服写真，你本人这张单人照，服饰与妆造：' + outfit + '，' + shape_name + '（' +
            size.replace('x', '×') + '），共' + str(count) + '张；' + DISCLOSURE + '，人脸和服饰细节可能有差异。'
            '照片会发送给' + RECIPIENTS + '处理。按张计费，以实际账单为准。' + NO_REPEAT)


def _link_label(link):
    name = unquote(link.rsplit('/', 1)[-1])
    return ''.join('\\' + c if c in '[]\\*_`' else c for c in name)


def delivery(links, remaining, first_time, title, size_note='', gallery_link=''):
    """links / gallery_link 必须是已做 Markdown 安全编码的链接目标（studio.md_safe_path）。"""
    lines = ['做好了（' + DISCLOSURE + '）：']
    for p in links:
        lines.append('- [' + _link_label(p) + '](' + p + ')')
    if gallery_link:
        lines.append('- [全部结果一览](' + gallery_link + ')')
    lines.append('这次做成了「' + title + '」主题，换了服饰、妆造、背景和光影，尽量保持五官、肤色和体态，发型按套系换成相应髻式；'
                 'AI 生成的效果可能与本人有差异，请放大看看脸部和手部。')
    if size_note:
        lines.append(size_note)
    lines.append(ORIGINAL_KEPT)
    if remaining is None:
        lines.append('本次费用以服务记录为准。')
    else:
        lines.append('本次费用以服务记录为准，剩余 ' + str(remaining) + ' 次。')
    if first_time:
        lines.append('想调整直接说，比如「换成更素雅的配色」「背景换成浅木色」「改成方图」。' + ONE_CHANGE + '需要重新生成的调整可能再次按张计费，我会先跟你确认。')
    return '\n'.join(lines)


def photo_changed():
    return ('你确认时用的那张照片，文件后来有了变化。为了不做错照片，这次还没有开始制作，没有产生任何扣费。'
            '请把要用的照片再发我一次，我按原来的方向重新跟你确认后再开始。')


def replan_pending():
    return ('方案有了改动，原来的确认已经作废，这次还没有开始制作，没有产生任何扣费。'
            '等这次改动需要的信息补齐、你再确认一次新方案后我才开始；想按原来的方案做，也请再确认一次。')


def size_mismatch(actual, requested):
    return '这次实际出图尺寸是 ' + actual + '，不是 ' + requested + '。画面比例以实际文件为准，需要固定尺寸时可以再裁切。'


def failure(reason_kind, charge_kind):
    reason = {
        'busy': '服务正在处理较多请求',
        'network': '网络连不上',
        'stale': '刚取到的链接已经过期，这一步还没完成',
        'rejected': '这张照片暂时无法按这个主题处理',
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


def account_summary(remaining, cards=None, total=None):
    lines = ['剩余可用次数：' + str(remaining) + ' 次']
    if cards is None:
        lines.append('消费记录这次没取到，稍后说「消费记录」我再查一次。')
    elif not cards:
        lines.append('还没有消费记录。')
    else:
        lines.append('最近记录：')
        lines += cards
        lines.append('共 ' + str(total) + ' 条，回复「查看所有」可看全部。')
    lines.append(HISTORY_SCOPE)
    lines.append('需要补充次数时，回复「充值」我为你打开充值页。')
    return '\n'.join(lines)


HISTORY_SCOPE = '记录包含同一账户在已接入技能里的通用次数使用情况。'
_JOB_STATUS = {'succeeded': '已完成', 'pending': '处理中', 'needs_review': '核对中', 'failed': '未完成'}


def history_card(when, content, charged, reserved, refunded, status):
    if isinstance(charged, int):
        fee = '未扣次' if charged == 0 else '扣 ' + str(charged) + ' 次'
    elif isinstance(reserved, int) and reserved > 0:
        fee = '预留 ' + str(reserved) + ' 次，完成后结算'
    else:
        fee = '扣次以服务记录为准'
    if isinstance(refunded, int) and refunded > 0:
        fee += '，已退回 ' + str(refunded) + ' 次'
    return '- ' + when + ' · ' + content + '\n  ' + fee + ' · ' + _JOB_STATUS.get(status, '其他')


def history_page(cards, total, page, has_more):
    if not cards:
        return '这一页没有记录，共 ' + str(total) + ' 条。'
    lines = ['消费记录（第 ' + str(page) + ' 页，共 ' + str(total) + ' 条）：'] + cards
    if has_more:
        lines.append('还有更多，回复「下一页」继续看。')
    lines.append(HISTORY_SCOPE)
    return '\n'.join(lines)


def history_unavailable():
    return '消费记录这次没取到，稍后说「消费记录」我再查一次。'


_CATEGORY = {'billing': '费用与次数', 'image_quality': '出图效果', 'workflow': '使用流程', 'suggestion': '建议与表扬', 'other': '其他'}
_TICKET_STATUS = {'open': '已受理，等待处理', 'in_progress': '处理中', 'resolved': '已处理'}


def _due(due_text):
    if due_text:
        return '预计处理时间：' + due_text + ' 前。'
    return '目前没有承诺具体处理时限，有回复后说「查工单」就能看到。'


def ticket_created(ticket_id, category, due_text):
    return '\n'.join([
        '你的反馈已经提交。',
        '反馈编号：' + ticket_id + '（' + _CATEGORY.get(category, '其他') + '）',
        _due(due_text),
        '之后说「查工单」就能看到处理进度和回复。提交反馈不扣次数。',
    ])


def ticket_view(ticket_id, category, status, reply, due_text):
    lines = ['反馈编号：' + ticket_id + '（' + _CATEGORY.get(category, '其他') + '）',
             '处理状态：' + _TICKET_STATUS.get(status, '处理中')]
    if reply:
        lines.append('回复：' + reply)
    else:
        lines.append('暂时还没有回复。')
        lines.append(_due(due_text))
    return '\n'.join(lines)


def tickets_none():
    return '这台设备上还没有提交过反馈。想反馈问题或提建议，直接告诉我就行。'


def ticket_not_found():
    return '没有找到这个反馈编号，请核对一下编号；也可以直接说「查工单」查看这台设备提交过的反馈。'


def feedback_saved(reason):
    head = {
        'no_account': '这台设备还没有关联账户，反馈单需要账户才能提交。',
        'busy': '服务正在处理较多请求，反馈这次没能提交。',
        'network': '网络暂时连不上，反馈这次没能提交。',
    }.get(reason, '反馈这次没能提交。')
    tail = '完成授权后说「提交反馈」，我再交一次。' if reason == 'no_account' else '稍后说「提交反馈」，我再交一次。'
    return head + '你的原话已经在本机记下，不用重说；' + tail + '提交反馈不扣次数。'


def feedback_nothing_pending():
    return '没有待提交的反馈。'


def ticket_lookup_failed(reason_kind):
    head = '网络暂时连不上' if reason_kind == 'network' else '服务正在处理较多请求'
    return head + '，这次没查到反馈进度。稍后说「查工单」我再查一次。'


def too_frequent():
    return '查询太频繁了，请稍等一分钟再试。'


def account_link(url, retry_word='充值'):
    """本机还没有账户的新用户要充值、付费链接或查账户时：给关联链接，不回死胡同。"""
    return '\n'.join([
        '这台设备还没有关联账户，先关联一次就能充值和查账户。',
        '',
        '### 现在需要你做的',
        '1. 点开关联链接：[关联账户](' + url + ')',
        '2. 扫码确认后会直接进入充值页，档位和金额都在页面上，按需选择；关联本身不扣费。',
        '3. 链接几分钟内有效；页面打不开或过期了，再跟我说一次「' + retry_word + '」，我重新取链接。',
        '',
        CROSS_SKILL,
    ])


def account_failure(reason_kind, retry_word='充值'):
    """账户类命令没拿到结果：按网络/繁忙如实说明，不猜原因。"""
    reason = {
        'network': '网络暂时没连上',
        'busy': '服务正在处理较多请求，这一步还没完成',
        'stale': '刚取到的链接已经过期，这一步还没完成',
    }[reason_kind]
    return reason + '，没有扣任何次数，稍后再说一次「' + retry_word + '」。'


def account_missing():
    return '这台设备上还没有关联账户。确认好汉服写真方案后，我会带你完成一次授权，授权本身不扣费。'


def input_error(filename, problem):
    return '照片「' + filename + '」' + problem + '，这次没有发送，也没有扣次数。换一张清晰的 PNG 或 JPG 照片发我就行。'


def refuse_misuse():
    return ('这个需求我不能处理：本技能只用成年用户本人知情同意的单人照制作汉服写真，'
            '不换脸，不做名人或别人的照片，不做未成年人，不把几张照片里的人合成到一起，不加入孩子或其他人，'
            '不做婚服、旗袍、和服或军装造型，也不做证件或任何证明用途的图片，不提供年龄判断或考古鉴定。')


def favorite_done():
    return '已收藏，以后问汉服写真、古风写真问题会优先由' + SKILL_NAME + '接待。想取消时说「取消收藏' + SKILL_NAME + '」即可。'


def favorite_unsupported():
    return '当前环境暂不支持收藏技能。'
