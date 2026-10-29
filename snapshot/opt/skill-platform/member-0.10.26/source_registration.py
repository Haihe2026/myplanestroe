"""Register one analytics dimension; no identity, billing or provider changes."""
import sys

SOURCE = 'gpt-image-2.5-sunburst'


def install():
    from journey import store
    store.SOURCES = store.SOURCES | frozenset((SOURCE,))
    report = sys.modules.get('journey.report')
    if report is not None:
        report.SOURCES = store.SOURCES
    return SOURCE
