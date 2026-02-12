---
layout: page
title: research
permalink: /research/
description:
nav: true
nav_order: 2
display_categories:
horizontal: true
---
Our body is a complex system. Each cell in our body can have different roles and developmental trajetories, even though they usually have the same genes. The diversity is mainly driven by the way genes are turned on and off in specific places and times. This precious regulation process is controlled by different elements in our genome, through various chemical modifications and conformation changes in DNA or associated proteins, all of which make up what we call the epigenome.

Being able to probe the dynamics of the epigenome in individual cells can provide insights into a cell's history, and in some cases, predict its future. This knowledge is crucial for mapping the complex landscapes of biological processes, and designing more precise and effective therapies for diseases. 

My current research focuses on developing a toolkit to measure various types of epigenetic changes at the single-cell level. This will enable us to capture a comprehensive picture of how these changes influence cell function and disease progression.



<!-- pages/projects.md -->
<div class="projects">
{% if site.enable_project_categories and page.display_categories %}
  {% for category in page.display_categories %}
  <a id="{{ category }}" href=".#{{ category }}">
    <h2 class="category">{{ category }}</h2>
  </a>
  {% assign categorized_projects = site.projects | where: "category", category %}
  {% assign sorted_projects = categorized_projects | sort: "importance" %}
  <div class="research-listing">
    {% for project in sorted_projects %}
      {% include projects_horizontal.liquid %}
    {% endfor %}
  </div>
  {% endfor %}
{% else %}
  {% assign sorted_projects = site.projects | sort: "importance" %}
  <div class="research-listing">
    {% for project in sorted_projects %}
      {% include projects_horizontal.liquid %}
    {% endfor %}
  </div>
{% endif %}
</div>
