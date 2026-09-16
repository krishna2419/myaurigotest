document.addEventListener('DOMContentLoaded', () => {
	const sidebar = document.querySelector('[data-sidebar]');
	const menuToggle = document.querySelector('[data-menu-toggle]');
	const menuClose = document.querySelector('[data-menu-close]');

	if (sidebar && menuToggle) {
		const closeMenu = () => sidebar.classList.remove('open');
		menuToggle.addEventListener('click', () => sidebar.classList.toggle('open'));
		menuClose?.addEventListener('click', closeMenu);
		sidebar.querySelectorAll('a').forEach((link) => link.addEventListener('click', closeMenu));
	}

	document.querySelectorAll('[data-filter-input]').forEach((input) => {
		const target = document.querySelector(input.dataset.filterInput);
		if (!target) return;
		const rows = target.querySelectorAll('[data-filter-row]');
		input.addEventListener('input', () => {
			const query = input.value.trim().toLowerCase();
			rows.forEach((row) => {
				row.hidden = query && !row.textContent.toLowerCase().includes(query);
			});
		});
	});
});
