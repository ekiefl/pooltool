{% if not obj.display %}
:orphan:

{% endif %}
``{{ obj.name }}``
{{ "=" * (obj.name|length + 4) }}

.. py:module:: {{ obj.name }}

{% if obj.docstring %}
{{ obj.docstring }}
{% endif %}

{% block subpackages %}
{% set visible_subpackages = obj.subpackages|selectattr("display")|list %}
{% if visible_subpackages %}
Subpackages
-----------
.. toctree::
   :titlesonly:
   :maxdepth: 1

{% for subpackage in visible_subpackages %}
   {{ subpackage.short_name }}/index.rst
{% endfor %}


{% endif %}
{% endblock %}
{% block submodules %}
{% set visible_submodules = obj.submodules|selectattr("display")|list %}
{% if visible_submodules %}
Submodules
----------
.. toctree::
   :titlesonly:
   :maxdepth: 1

{% for submodule in visible_submodules %}
   {{ submodule.short_name }}/index.rst
{% endfor %}

{% endif %}
{% endblock %}
{% block content %}
{% if obj.all is not none %}
{% set visible_children = obj.children|selectattr("display")|selectattr("short_name", "in", obj.all)|list %}
{% elif obj.type is equalto("package") %}
{% set visible_children = obj.children|selectattr("display")|list %}
{% else %}
{% set visible_children = obj.children|selectattr("display")|rejectattr("imported")|list %}
{% endif %}
{% if visible_children %}
{% set visible_classes = visible_children|selectattr("type", "equalto", "class")|list %}
{% set visible_functions = visible_children|selectattr("type", "equalto", "function")|list %}
{% set visible_attributes = visible_children|selectattr("type", "equalto", "data")|list %}
{% if visible_classes %}
Classes
-------
{% for obj_item in visible_classes %}
{{ obj_item.render()|indent(0) }}
{% endfor %}
{% endif %}

{% if visible_functions %}
Functions
---------
{% for obj_item in visible_functions %}
{{ obj_item.render()|indent(0) }}
{% endfor %}
{% endif %}

{% if visible_attributes %}
Attributes
----------
{% for obj_item in visible_attributes %}
{{ obj_item.render()|indent(0) }}
{% endfor %}
{% endif %}


{% endif %}
{% endblock %}
