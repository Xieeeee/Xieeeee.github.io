---
layout: page
title: resources
permalink: /resources/
description:
nav: true
nav_order: 5
---

Datasets and protocols that I have shared with the community.

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
