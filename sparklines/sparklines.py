from operator import itemgetter
from copy import copy

from jinja2 import Template
import numpy as np


SVG_BASE_TEMPLATE = Template("""
    {%- block svg_outer -%}
        <svg width="{{width}}"
             height="{{height}}"
             class="{{ class if class else 'svg' }}"
             version="1.1"
             xmlns="http://www.w3.org/2000/svg"
             >
          {%- block svg_inner -%}
          {% endblock %}
        </svg>
    {% endblock %}
    """)

SVG_MACROS = Template("""
    {% macro circle(x, y, fill, class="", r=2) -%}
        <circle cx="{{ x }}"
                cy="{{ y }}"
                r="{{ r }}"
                fill="{{ fill }}"
                class="{{ class }}"
                />
    {%- endmacro %}
    {% macro point(x, y) %}{{ x }},{{ y }} {% endmacro %}
    """)


class SparkBase(object):

    DEFAULTS = {
        'width': 150,
        'height': 20,
        'SVG_MACROS': SVG_MACROS,
    }

    def _render_inner(self):
        """Render SVG template."""
        return Template(self.TEMPLATE).render(self.context)

    def _render_outer(self):
        return Template(self.OUTER_TEMPLATE).render(
            self.context,
            SVG_BASE_TEMPLATE=SVG_BASE_TEMPLATE
        )

    def render(self):
        """Render SVG template."""
        return self._render_outer()

    def _repr_html_(self):
        return self.render()

    def __repr__(self):
        return self.render()

    def __str__(self):
        return self.render()

    @property
    def width(self):
        return self.context['width']

    @property
    def height(self):
        return self.context['height']

    def __add__(self, other):
        if isinstance(other, SparkBase):
            if self.width == other.width and self.height == other.height:
                return MultiSparkline([self, other])
            else:
                raise ValueError("Sparklines must have the same dimensions")
        raise TypeError("Cannot add to Sparkline")

    @property
    def OUTER_TEMPLATE(self):
        return "{}{}".format("{% extends SVG_BASE_TEMPLATE %}", self.TEMPLATE)


class Sparkline(SparkBase):
    """SVG Sparkline from numpy array.

    :param data:
        Array data to be used for line
    :param width: default 150px
        Width of svg
    :param height: default 20px
        Height of svg
    :param height_offset:
        Offset from top/bottom to line
    :param width_offset:
        Offset from sides to lines
    :param show_max:
        Show green dot indicating maximums
    :param show_min:
        Show red dot indicating minimums
    :param min_color:
        Color of dot representing minimum value
    :param max_color:
        Color of dot representing maximum value
    :param line_color:
        Color of lines
    :param ymin:
        Minimum y value on scale
    :param ymax:
        Maximum y value on scale
    """

    # flake8: noqa
    TEMPLATE = """
        {% from SVG_MACROS import circle, point %}

        {% block svg_inner -%}

            <polyline points="
                {%- for x, y in points -%}
                    {{ point(x, y) }}
                {%- endfor -%} "
                class="line"
                fill="transparent"
                stroke="{{ line_color }}"
                />

            {%- if show_start -%}
              {{ circle(points[0][0],
                        points[0][1],
                        line_color,
                        class="start",
                        r=height_offset)
              }}
            {% endif %}

            {%- if show_end -%}
              {{ circle(points[-1][0],
                        points[-1][1],
                        line_color,
                        class="end",
                        r=height_offset)
              }}
            {% endif %}

            {%- for x, y in maxs -%}
              {{ circle(x, y, max_color, class="max", r=height_offset) }}
            {% endfor %}

            {%- for x, y in mins -%}
              {{ circle(x, y, min_color, class="min", r=height_offset) }}
            {% endfor %}

        {%- endblock %}
    """

    DEFAULTS = dict(SparkBase.DEFAULTS,
                    height_offset=2.5,
                    width_offset=2.5,

                    show_max=False,
                    show_min=False,
                    show_start=False,
                    show_end=True,

                    min_color="#ff0000",
                    max_color="#8ca252",
                    line_color="#000000")

    def __init__(self, data, **kwargs):
        ctx = dict(self.DEFAULTS, **kwargs)

        width = ctx['width']
        height = ctx['height']
        width_offset = ctx['width_offset']
        height_offset = ctx['height_offset']

        data = np.array(data)

        ymin = ctx.get('ymin', data.min())
        ymax = ctx.get('ymax', data.max())
        scaled = (data - ymin) / (ymax - ymin)
        range = height - 2 * height_offset

        ys = height_offset + range * (1 - scaled)
        xs = np.linspace(width_offset, width - width_offset, num=data.size)
        points = list(zip(xs, ys))

        def get_condition(cnd):
            ix = np.where(cnd)
            return list(zip(xs[ix], ys[ix]))

        mins = get_condition(data == ymin) if ctx.get('show_min') else []
        maxs = get_condition(data == ymax) if ctx.get('show_max') else []

        self.context = dict(ctx,
                            points=points,
                            maxs=maxs,
                            mins=mins)


class SparkBar(SparkBase):

    TEMPLATE = """
        {% block svg_inner -%}
        {%- for x, y, w, h in bars -%}
            <rect
                x="{{ x }}"
                y="{{ y }}"
                width="{{ w }}"
                height="{{ h }}"
                fill="{{ bar_color }}"
                />
        {% endfor %}
        {% endblock %}
    """

    DEFAULTS = dict(SparkBase.DEFAULTS,
                    bar_spacing=0,
                    bar_color="#000000")

    def __init__(self, data, **kwargs):
        ctx = dict(self.DEFAULTS, **kwargs)

        width = ctx['width']
        height = ctx['height']
        bar_spacing = ctx['bar_spacing']

        data = np.array(data)
        size = data.size

        bar_width = width / (size + bar_spacing)

        ymin = ctx.get('ymin') or data.min()
        ymax = ctx.get('ymax') or data.max()
        scaled = height * (data - ymin) / (ymax - ymin)

        ys = height - scaled
        heights = scaled
        widths = np.array([bar_width for _ in range(size)])
        xs = (widths + bar_spacing).cumsum()

        bars = list(zip(xs, ys, widths, heights))

        self.context = dict(ctx, bars=bars)


class MultiSparkline(object):
    """MultiSparkline class used to stack Sparklines on the same axis

    Parameters:
    -----------
    :param values: List of Sparkline objects
    """

    TEMPLATE = Template("""
        {% extends SVG_BASE_TEMPLATE %}
        {% block svg_inner %}
            {% for sparkline in sparklines -%}
                {{ sparkline }}
            {%- endfor %}
        {% endblock %}
    """)

    def __init__(self, values=None):
        self.values = values or []
        self.width = values[0].width if values else 0
        self.height = values[0].height if values else 0

    def __add__(self, other):
        if isinstance(other, MultiSparkline):
            if self.width == other.width and self.height == other.height:
                return MultiSparkline(self.values + other.values)

        if isinstance(other, Sparkline):
            if self.width == other.width and self.height == other.height:
                return MultiSparkline(self.values + [other])

        raise TypeError("Only Sparkline and MultiSparkline objects may be "
                        "added to a MultiSparkline.")

    def get_context(self):
        return {
            'width': self.width,
            'height': self.height,
            'sparklines': (v._render_inner() for v in self.values)
        }

    def render(self):
        return self.TEMPLATE.render(self.get_context(),
                                    SVG_BASE_TEMPLATE=SVG_BASE_TEMPLATE)

    def _repr_html_(self):
        return self.render()

    def __repr__(self):
        return self.render()

    def __str__(self):
        return self.render()
