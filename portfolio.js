(() => {
  'use strict';

  document.getElementById('year').textContent = new Date().getFullYear();
  const chips = [...document.querySelectorAll('.chip')];
  const projects = [...document.querySelectorAll('.proj')];
  const count = document.getElementById('fcount');
  const validFilters = new Set(chips.map(chip => chip.dataset.f));

  function filterProjects(filter, updateURL = false) {
    if (!validFilters.has(filter)) filter = 'selected';
    let visible = 0;
    projects.forEach(project => {
      const show = filter === 'all'
        || (filter === 'selected' && project.hasAttribute('data-selected'))
        || project.dataset.cat.split(' ').includes(filter);
      project.hidden = !show;
      if (show) visible++;
    });
    chips.forEach(chip => chip.setAttribute('aria-pressed', String(chip.dataset.f === filter)));
    count.textContent = `${visible} of ${projects.length} projects`;
    if (updateURL) {
      const url = new URL(location.href);
      if (filter === 'selected') url.searchParams.delete('projects');
      else url.searchParams.set('projects', filter);
      url.hash = 'work';
      history.replaceState(null, '', url);
    }
  }

  // Without JavaScript every project remains readable; only working controls appear.
  chips.forEach(chip => chip.addEventListener('click', () => filterProjects(chip.dataset.f, true)));
  filterProjects(new URL(location.href).searchParams.get('projects') || 'selected');
  document.querySelector('.filters').hidden = false;

  const dialog = document.getElementById('pal');
  if (typeof dialog.showModal !== 'function') return;
  const query = document.getElementById('pal-q');
  const list = document.getElementById('pal-list');
  const status = document.getElementById('pal-status');
  const openButton = document.getElementById('pal-open');
  let results = [];
  let selected = 0;
  let previousFocus;
  const destinations = [
    ['Projects', 'section', '#work'],
    ['Evidence hub: seven data and ML capabilities', 'evidence', './labs/'],
    ['Experimentation decision report', 'evidence', './labs/experimentation/'],
    ['Nested churn evaluation', 'evidence', './labs/churn/'],
    ['Document search lifecycle', 'evidence', './labs/search/'],
    ['Historical management decision brief', 'evidence', './labs/management/'],
    ['Demand forecasting and capacity scenario', 'evidence', './labs/forecast/'],
    ['Customer future-value study', 'evidence', './labs/customer-value/'],
    ['Booking-time prediction service evaluation', 'evidence', './labs/service/'],
    ['AI regression evaluation gate', 'evidence', './labs/evaluation/'],
    ['Professional experience', 'section', '#experience'],
    ['About', 'section', '#about'],
    ['Toolkit', 'section', '#skills'],
    ['Contact', 'section', '#contact'],
    ['Professional case study: Gosian Media', 'case study', './gosian/'],
    ['CV, data engineering (PDF)', 'document', './vasilen-kanchev-cv.pdf'],
    ['CV, analytics (PDF)', 'document', './vasilen-kanchev-cv-analytics.pdf'],
    ['LinkedIn', 'link', 'https://www.linkedin.com/in/vasilenkanchev/'],
    ['GitHub', 'link', 'https://github.com/VasilenData'],
    ['Email', 'contact', 'mailto:vasilen.business@gmail.com'],
  ].map(([title, type, href]) => ({ title, type, href, keywords: title.toLowerCase() }));

  projects.forEach(project => {
    const title = project.querySelector('h3').textContent;
    const links = [...project.querySelectorAll('a.go')];
    links.forEach((link, index) => destinations.push({
      title: index ? `${title} — ${link.textContent.replace('↗', '').trim()}` : title,
      type: 'project',
      href: link.getAttribute('href'),
      keywords: project.textContent.toLowerCase(),
    }));
  });

  function mark(scroll = true) {
    [...list.querySelectorAll('[role="option"]')].forEach((option, index) => {
      option.setAttribute('aria-selected', String(index === selected));
      if (index === selected && scroll) option.scrollIntoView({ block: 'nearest' });
    });
    if (results.length) query.setAttribute('aria-activedescendant', `pal-option-${selected}`);
    else query.removeAttribute('aria-activedescendant');
  }

  function draw() {
    const terms = query.value.toLowerCase().trim().split(/\s+/).filter(Boolean);
    results = destinations.filter(item => terms.every(term => `${item.keywords} ${item.type}`.includes(term)));
    selected = 0;
    list.replaceChildren();
    status.textContent = `${results.length} search results`;
    if (!results.length) {
      const empty = document.createElement('li');
      empty.className = 'none';
      empty.textContent = 'No results. Try a project name or a skill such as Python.';
      list.append(empty);
    }
    results.forEach((item, index) => {
      const option = document.createElement('li');
      option.id = `pal-option-${index}`;
      option.setAttribute('role', 'option');
      const title = document.createElement('span');
      title.textContent = item.title;
      const type = document.createElement('small');
      type.textContent = item.type;
      option.append(title, type);
      option.addEventListener('click', () => go(index));
      list.append(option);
    });
    mark(false);
  }

  function go(index) {
    const destination = results[index];
    if (!destination) return;
    dialog.close();
    if (destination.href.startsWith('#')) {
      const target = document.querySelector(destination.href);
      location.hash = destination.href;
      // Move keyboard focus with the visible navigation, rather than back to search.
      target.setAttribute('tabindex', '-1');
      target.focus({ preventScroll: true });
      previousFocus = target;
    } else if (/^https:/.test(destination.href)) {
      window.open(destination.href, '_blank', 'noopener');
    } else {
      location.href = destination.href;
    }
  }

  function open() {
    previousFocus = document.activeElement;
    query.value = '';
    draw();
    dialog.showModal();
    query.focus();
  }

  openButton.hidden = false;
  openButton.addEventListener('click', open);
  document.getElementById('pal-close').addEventListener('click', () => dialog.close());
  document.addEventListener('keydown', event => {
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k') {
      event.preventDefault();
      if (dialog.open) dialog.close();
      else open();
    }
  });
  query.addEventListener('input', draw);
  query.addEventListener('keydown', event => {
    if (event.key === 'Enter') {
      event.preventDefault();
      go(selected);
    } else if (['ArrowDown', 'ArrowUp', 'Home', 'End'].includes(event.key) && results.length) {
      if ((event.key === 'Home' || event.key === 'End') && !event.ctrlKey) return;
      event.preventDefault();
      if (event.key === 'Home') selected = 0;
      else if (event.key === 'End') selected = results.length - 1;
      else selected = (selected + (event.key === 'ArrowDown' ? 1 : -1) + results.length) % results.length;
      mark();
    }
  });
  dialog.addEventListener('close', () => previousFocus?.focus({ preventScroll: true }));
  dialog.addEventListener('click', event => {
    if (event.target !== dialog) return;
    const bounds = dialog.getBoundingClientRect();
    if (event.clientX < bounds.left || event.clientX > bounds.right || event.clientY < bounds.top || event.clientY > bounds.bottom) dialog.close();
  });
})();
