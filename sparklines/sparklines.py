from collections import Iterable
import xml.etree.ElementTree as ET

# from jinja2 import Template
import numpy as np


def cdata(s):
    return "<![CDATA[{}]]>".format(s)


DEFAULT_STROKE_WIDTH = 2


class SparkBase(object):

    def __init__(self, width=150, height=25, **kwargs):
        self.width = width
        self.height = height
        self.local_css = []

    @property
    def CSS(self):
        return "\n".join(self.local_css)

    @property
    def root(self):
        root = ET.Element('svg', attrib={
            'xmlns': 'http://www.w3.org/2000/svg',
            'version': '1.1',
            'width': str(self.width),
            'height': str(self.height),
        })

        style = ET.SubElement(root, 'style')
        style.text = '__CSS__'
        style.set('type', 'text/css')
        return root

    def inner(self, root):
        return root

    def render(self):
        return ET.tostring(self.inner(self.root)).replace('__CSS__', cdata(self.CSS), 1)

    def __repr__(self):
        return str(self)

    def __str__(self):
        return self.render()

    def _as_img(self):
        return "data:image/svg+xml;utf-8,{src}".format(
            src=self.render().replace('"', "'")
        )

    def _repr_html_(self):
        # return self.render()
        return '<img width="{width}" height="{height}" src="{src}">'.format(
            width=self.width,
            height=self.height,
            src=self._as_img(),
        )

    def __add__(self, other):
        if isinstance(other, SparkBase):
            left = MultiSparkline(
                [self],
                width=self.width,
                height=self.height
            )
            return left.add(other)
        else:
            raise ValueError("Cannot add this object to sparkline")


def normalize(x):
    """Scale array to [0, 1]"""
    _, (xmin, xmax) = np.histogram(x, bins=1)
    return (x - xmin) / (xmax - xmin)


class Sparkline(SparkBase):
    """Classic Solid sparkline """

    def __init__(
            self,
            y,
            x=None,
            color='#000000',
            cls='sparkline',
            stroke_width=DEFAULT_STROKE_WIDTH,
            name=None,
            alpha=1,
            **kwargs):
        """
        param x: array of x values
        param y: array of y values
        """
        super(Sparkline, self).__init__(**kwargs)
        self.cls = cls
        self.name = name if name is not None else "sparkline_{}".format(id(self))

        self.stroke_width = stroke_width
        self.x = x
        self.y = y

        self.local_css.append(
            """
            #{id} polyline {{
                stroke: {color};
                stroke-width: {stroke_width};
                fill: transparent;
                opacity: {alpha};
            }}
            """.format(
                id=self.name,
                color=color,
                stroke_width=self.stroke_width,
                alpha=alpha
            )
        )

    def inner(self, root):
        base = ET.SubElement(root, 'g')
        base.set('class', self.cls)

        if self.name:
            base.set('id', str(self.name))

        y = self.y
        x = self.x
        stroke_width = self.stroke_width

        y = (1 - normalize(y)) * (self.height - 2 * stroke_width) + stroke_width

        x = x if x is not None else np.linspace(0, 1, len(y))
        x = (normalize(x)) * (self.width - 2 * stroke_width) + stroke_width

        points = " ".join(
            ["{:.5f},{:.5f}".format(_x, _y) for _x, _y in zip(x, y)]
        )

        ET.SubElement(base, 'polyline', attrib={
            'points': points,
        })
        return root


class Sparkblock(SparkBase):
    """Highlited block on a Sparkline

    Can be used to highlight a confidence interval or differentiate periods.
    """

    def __init__(
            self, x, y,
            color='#3cb371',
            alpha=0.25,
            cls='sparkblock',
            name=None,
            stroke_width=DEFAULT_STROKE_WIDTH,
            **kwargs):
        """
        param x: x values used to sync between sparkline and block
        param y: array of true/false values specifying where block starts and
                 ends. Must be contiguous with no breaks or gaps.
        """
        super(Sparkblock, self).__init__(**kwargs)
        self.cls = cls
        self.name = name if name is not None else "sparkblock_{}".format(id(self))
        self.stroke_width = stroke_width

        self.x = x
        self.y = y

        self.local_css.append(
            """
            #{id} rect {{
                fill: {color};
                opacity: {alpha};
            }}
            """.format(
                id=self.name,
                color=color,
                stroke_width=stroke_width,
                alpha=alpha,
            )
        )

    def inner(self, root):
        base = ET.SubElement(root, 'g')
        base.set('class', self.cls)
        if self.name:
            base.set('id', str(self.name))

        x = self.x
        y = self.y
        stroke_width = self.stroke_width

        x = (normalize(x)) * (self.width - 2 * stroke_width) + stroke_width

        ixs = np.argwhere(y)
        if len(ixs):
            start = ixs[0][0]
            end = ixs[-1][0]
            start = x[start]
            end = x[end]
        else:
            start = end = None

        if not start or not end:
            return root

        x = start
        y = 0
        w = end - start
        h = self.height

        ET.SubElement(base, 'rect', attrib={
            'x': str(x),
            'y': str(y),
            'width': str(w),
            'height': str(h),
        })
        return root


class MultiSparkline(SparkBase):
    """Composition of Sparkline objects.

    Objects are composed in the order they are input, with the last objects
    added being drawn at the top of the SVG.
    """

    def __init__(self, *children, **kwargs):
        super(MultiSparkline, self).__init__(**kwargs)

        self.children = []
        for c in children:
            if isinstance(c, SparkBase):
                self.children.append(c)
            elif isinstance(c, Iterable):
                self.children.extend(c)

        for child in self.children:
            self.local_css += child.local_css

    def add(self, other):
        if isinstance(other, MultiSparkline):
            return MultiSparkline(self.children + other.children)
        elif isinstance(other, SparkBase):
            return MultiSparkline(self.children + [other])
        else:
            raise ValueError("Can only combine sparkline objects.")

    def inner(self, root):
        for child in self.children:
            child.width = self.width
            child.height = self.height
            child.inner(root)
        return root
