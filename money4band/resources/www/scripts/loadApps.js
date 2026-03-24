window.onload = () => {
    fetch('/api/config/app')
      .then(response => response.json())
      .then(config => {
        const tableBody = document.querySelector('.u-table-body');

        // Function to create rows for each app category
        const createAppRows = (entries, categoryTitle, isActive) => {
          if (!entries || entries.length === 0) return;

          const categoryHeader = document.createElement('tr');
          const categoryTitleCell = document.createElement('td');
          categoryTitleCell.colSpan = 3;
          categoryTitleCell.style.fontWeight = 'bold';
          const statusBadge = isActive
            ? '<span style="color:green">[ACTIVE]</span>'
            : '<span style="color:red">[INACTIVE]</span>';
          categoryTitleCell.innerHTML = `${categoryTitle} ${statusBadge}`;
          categoryHeader.appendChild(categoryTitleCell);
          tableBody.appendChild(categoryHeader);

          entries.forEach((app, index) => {
            const tr = document.createElement('tr');
            tr.style.height = '52px';
            if (!isActive) tr.style.opacity = '0.6';

            const tdName = document.createElement('td');
            tdName.className = 'u-border-2 u-border-grey-10 u-border-no-left u-border-no-right u-table-cell';
            let nameText = app.name;
            if (!isActive && app.removal_reason) {
              nameText += ` (${app.removal_reason})`;
            }
            tdName.textContent = nameText;

            const tdDashboard = document.createElement('td');
            tdDashboard.className = 'u-border-2 u-border-grey-10 u-border-no-left u-border-no-right u-table-cell';
            tdDashboard.innerHTML = `<a class="u-active-none u-border-none u-btn u-button-link u-button-style u-hover-none u-none u-text-palette-1-base u-btn-${index+1}" href="${app.dashboard}" target="_blank" rel="nofollow">Dashboard</a>`;

            const tdInvite = document.createElement('td');
            tdInvite.className = 'u-border-2 u-border-grey-10 u-border-no-left u-border-no-right u-table-cell';
            tdInvite.innerHTML = `<a class="u-active-none u-border-none u-btn u-button-link u-button-style u-hover-none u-none u-text-palette-1-base u-btn-${index+2}" href="${app.link}" target="_blank">Invite friends</a>`;

            tr.appendChild(tdName);
            tr.appendChild(tdDashboard);
            tr.appendChild(tdInvite);

            tableBody.appendChild(tr);
          });
        };

        // Render all categories (active first, then inactive)
        const categories = Object.keys(config).filter(
          key => config[key] && typeof config[key] === 'object' && Array.isArray(config[key].entries)
        );
        const active = categories.filter(c => config[c].active);
        const inactive = categories.filter(c => !config[c].active);

        for (const cat of [...active, ...inactive]) {
          const title = cat.charAt(0).toUpperCase() + cat.slice(1);
          createAppRows(config[cat].entries, title, config[cat].active);
        }
      })
      .catch(error => console.error('Error:', error));
  };