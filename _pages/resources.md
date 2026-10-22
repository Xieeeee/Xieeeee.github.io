---
layout: page
title: resources
permalink: /resources/
description:
nav: true
nav_order: 5
---

Methods and data that my team have contributed to the scientific community.

<!-- pages/resources.md -->
<div class="resources">
{% for group in site.data.resources %}
  <section class="resource-section">
    <h2 class="resource-section__title">{{ group.section }}</h2>
    {% for resource in group.items %}
      {% include resource_row.liquid %}
    {% endfor %}
  </section>
{% endfor %}
</div>
