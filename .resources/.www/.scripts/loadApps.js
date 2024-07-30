window.onload = () => {
    fetch('.config/app-config.json')
      .then(response => response.json())
      .then(config => {
        const tableBody = document.querySelector('.u-table-body');
        
        // Function to create rows for each app category
        const createAppRows = (appCategory, categoryTitle) => {
          const categoryHeader = document.createElement('tr');
          const categoryTitleCell = document.createElement('td');
          categoryTitleCell.colSpan = 3; // Spanning across three columns
          categoryTitleCell.style.fontWeight = 'bold'; // Making the title bold
          categoryTitleCell.textContent = categoryTitle;
          categoryHeader.appendChild(categoryTitleCell);
          tableBody.appendChild(categoryHeader);

          appCategory.forEach((app, index) => {
            const tr = document.createElement('tr');
            tr.style.height = '52px';

            const tdName = document.createElement('td');
            tdName.className = 'u-border-2 u-border-grey-10 u-border-no-left u-border-no-right u-table-cell';
            tdName.textContent = app.name;

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

        // Creating rows for each app category
        createAppRows(config.apps, "Apps");
        createAppRows(config['extra-apps'], "Extra-apps");
        createAppRows(config['removed-apps'], "Removed-apps");
      })
      .catch(error => console.error('Error:', error));
  };