"""Bounded, inert diagrams and portable HTML built from saved note data."""
from html import escape
import math
import textwrap


def validate_diagram(diagram):
    nodes = [node['id'] for node in diagram['nodes']]
    if len(nodes) != len(set(nodes)):
        raise ValueError('duplicate_diagram_node')
    for edge in diagram['edges']:
        if edge['from'] not in nodes or edge['to'] not in nodes or edge['from'] == edge['to']:
            raise ValueError('invalid_diagram_edge')


def diagram_svg(diagram):
    """Render only our own shapes; model strings are always escaped text."""
    validate_diagram(diagram)
    nodes = diagram['nodes']
    width, height = max(920, len(nodes) * 110), max(520, len(nodes) * 85)
    cx, cy = width / 2, height / 2
    positions = {}
    for index, node in enumerate(nodes):
        angle = 2 * math.pi * index / len(nodes) - math.pi / 2
        positions[node['id']] = (cx + (width / 2 - 140) * math.cos(angle), cy + (height / 2 - 90) * math.sin(angle))
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" role="img">',
           '<title>' + escape(diagram['caption']) + '</title>',
           f'<rect width="{width}" height="{height}" fill="#f8fafc"/>']
    for index, edge in enumerate(diagram['edges']):
        x1, y1 = positions[edge['from']]; x2, y2 = positions[edge['to']]
        dx, dy = x2 - x1, y2 - y1
        length = math.hypot(dx, dy)
        ux, uy = dx / length, dy / length
        # End at the rectangular node boundary and draw an explicit arrow head.
        scale = min(90 / max(abs(ux), .001), 40 / max(abs(uy), .001))
        ex, ey = x2 - ux * scale, y2 - uy * scale
        out.append(f'<path d="M{x1:.1f},{y1:.1f} L{ex:.1f},{ey:.1f}" stroke="#475569" stroke-width="2" fill="none"/>')
        out.append(f'<path d="M{ex:.1f},{ey:.1f} l{-ux*12-uy*6:.1f},{-uy*12+ux*6:.1f} l{uy*12:.1f},{-ux*12:.1f} Z" fill="#475569"/>')
        lx, ly = x1 + dx * (.35 + .1 * (index % 3)), y1 + dy * (.35 + .1 * (index % 3))
        for line, label in enumerate(textwrap.wrap(edge['label'], 23)):
            label_width = len(label) * 8 + 12
            out.append(f'<rect x="{lx-label_width/2:.1f}" y="{ly+line*16-13:.1f}" width="{label_width}" height="17" fill="#f8fafc"/>')
            out.append(f'<text x="{lx:.1f}" y="{ly+line*16:.1f}" text-anchor="middle" font-family="sans-serif" font-size="13" fill="#0f172a">{escape(label)}</text>')
    for node in nodes:
        x, y = positions[node['id']]
        out.append(f'<rect x="{x-90:.1f}" y="{y-40:.1f}" width="180" height="80" rx="12" fill="#dbeafe" stroke="#2563eb"/>')
        labels = textwrap.wrap(node['label'], 23)
        for index, label in enumerate(labels):
            out.append(f'<text x="{x:.1f}" y="{y-(len(labels)-1)*8+index*16+5:.1f}" text-anchor="middle" font-family="sans-serif" font-size="14" fill="#0f172a">{escape(label)}</text>')
    return ''.join(out) + '</svg>'


def diagram_description(diagram):
    names = {node['id']: node['label'] for node in diagram['nodes']}
    return '\n'.join(f"{names[e['from']]} → {names[e['to']]}: {e['label']}" for e in diagram['edges'])


def diagram_stale(block):
    return block.get('student_edited') or any(p.get('student_edited') for p in block['passages'])


def html_notes(title, content, source_markdown):
    out = ['<!doctype html><html lang="en"><meta charset="utf-8">',
           '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\'; base-uri \'none\'; form-action \'none\'">',
           '<meta name="viewport" content="width=device-width,initial-scale=1">',
           '<title>' + escape(title) + '</title>',
           '<style>body{max-width:960px;margin:40px auto;padding:0 24px;color:#172033;font:17px/1.6 system-ui;background:#fff}section{margin:32px 0}svg{width:100%;height:auto}p,pre{white-space:pre-wrap;overflow-wrap:anywhere}pre{font-size:14px}small{color:#475569}figure{margin:24px 0}h1,h2{line-height:1.2}</style>',
           '<body><h1>' + escape(title) + '</h1><p>Selected saved revision. Diagrams are AI-created schematics from cited text, not captured lecture visuals. Check scientific accuracy against the sources.</p>']
    for block in content['blocks']:
        out.append('<section><h2>' + escape(block['topic']) + '</h2>')
        for passage in block['passages']:
            out.append('<p>' + escape(passage['text']) + '</p><small>Sources: ' + escape(', '.join(c['source_id'] for c in passage['sources']) or 'Student addition') + '</small>')
        if block.get('diagram'):
            diagram = block['diagram']
            out.append('<figure>' + diagram_svg(diagram) + '<figcaption>' + escape(diagram['caption']) + '</figcaption></figure>')
            if diagram_stale(block):
                out.append('<p>Review diagram: this section has student changes; the original diagram is retained.</p>')
            out.append('<pre>' + escape(diagram_description(diagram)) + '</pre>')
        out.append('</section>')
    out.append('<h2>Saved revision, evidence and review record</h2><pre>' + escape(source_markdown) + '</pre></body></html>')
    return ''.join(out)
