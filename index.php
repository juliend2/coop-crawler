<?php
/**
 * FHCQ Cooperatives Listing Display
 * Displays listings from the SQLite database in a nice table format
 */

// Database connection
$db_path = __DIR__ . '/cooperatives.db';

if (!file_exists($db_path)) {
    die("Database file not found. Please run the crawler first.");
}

try {
    $db = new PDO("sqlite:$db_path");
    $db->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);
} catch (PDOException $e) {
    die("Database connection failed: " . $e->getMessage());
}

// Get filter parameters
$zone_filter = isset($_GET['zone']) ? (int)$_GET['zone'] : null;
$sector_filter = isset($_GET['sector']) ? $_GET['sector'] : null;
$dwelling_filter = isset($_GET['dwelling']) ? (int)$_GET['dwelling'] : null;
$parking_filter = isset($_GET['parking']) ? $_GET['parking'] : null;

// Build query
$query = "SELECT * FROM listings WHERE 1=1";
$params = [];

if ($zone_filter !== null && $zone_filter > 0) {
    $query .= " AND zone = ?";
    $params[] = $zone_filter;
}

if ($sector_filter) {
    $query .= " AND sector = ?";
    $params[] = $sector_filter;
}

if ($dwelling_filter) {
    $query .= " AND dwelling_type = ?";
    $params[] = $dwelling_filter;
}

if ($parking_filter === 'car') {
    $query .= " AND has_car_parking = 1";
} elseif ($parking_filter === 'bike') {
    $query .= " AND has_bike_parking = 1";
}

// Sorting
$sort = isset($_GET['sort']) ? $_GET['sort'] : 'name';
$order = isset($_GET['order']) && strtoupper($_GET['order']) === 'DESC' ? 'DESC' : 'ASC';
$allowed_sort = ['name', 'address', 'sector', 'zone', 'dwelling_type'];
if (!in_array($sort, $allowed_sort)) {
    $sort = 'name';
}
$query .= " ORDER BY $sort $order";

// Execute query
$stmt = $db->prepare($query);
$stmt->execute($params);
$listings = $stmt->fetchAll(PDO::FETCH_ASSOC);

// Get statistics
$stats_query = "SELECT 
    COUNT(*) as total,
    COUNT(DISTINCT zone) as zones,
    COUNT(DISTINCT sector) as sectors,
    SUM(has_car_parking) as with_car_parking,
    SUM(has_bike_parking) as with_bike_parking
    FROM listings";
$stats = $db->query($stats_query)->fetch(PDO::FETCH_ASSOC);

// Get unique sectors and zones for filters
$sectors_query = "SELECT DISTINCT sector FROM listings WHERE sector IS NOT NULL ORDER BY sector";
$sectors = $db->query($sectors_query)->fetchAll(PDO::FETCH_COLUMN);

$zones_query = "SELECT DISTINCT zone FROM listings WHERE zone IS NOT NULL ORDER BY zone";
$zones = $db->query($zones_query)->fetchAll(PDO::FETCH_COLUMN);
?>
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>FHCQ Cooperatives - Liste des coopératives</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }

        .container {
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
            overflow: hidden;
        }

        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }

        .header h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
        }

        .header p {
            opacity: 0.9;
            font-size: 1.1em;
        }

        .stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            padding: 30px;
            background: #f8f9fa;
        }

        .stat-card {
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
            text-align: center;
        }

        .stat-card .number {
            font-size: 2.5em;
            font-weight: bold;
            color: #667eea;
            margin-bottom: 5px;
        }

        .stat-card .label {
            color: #666;
            font-size: 0.9em;
            text-transform: uppercase;
            letter-spacing: 1px;
        }

        .filters {
            padding: 30px;
            background: #f8f9fa;
            border-top: 1px solid #e0e0e0;
        }

        .filters form {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            align-items: end;
        }

        .filter-group {
            display: flex;
            flex-direction: column;
        }

        .filter-group label {
            margin-bottom: 5px;
            font-weight: 600;
            color: #333;
            font-size: 0.9em;
        }

        .filter-group select,
        .filter-group input {
            padding: 10px;
            border: 2px solid #e0e0e0;
            border-radius: 6px;
            font-size: 1em;
            transition: border-color 0.3s;
        }

        .filter-group select:focus,
        .filter-group input:focus {
            outline: none;
            border-color: #667eea;
        }

        .btn {
            padding: 10px 20px;
            background: #667eea;
            color: white;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            font-size: 1em;
            font-weight: 600;
            transition: background 0.3s;
        }

        .btn:hover {
            background: #5568d3;
        }

        .btn-secondary {
            background: #6c757d;
        }

        .btn-secondary:hover {
            background: #5a6268;
        }

        .table-container {
            padding: 30px;
            overflow-x: auto;
        }

        table {
            width: 100%;
            border-collapse: collapse;
            background: white;
        }

        thead {
            background: #667eea;
            color: white;
        }

        th {
            padding: 15px;
            text-align: left;
            font-weight: 600;
            cursor: pointer;
            user-select: none;
            position: relative;
        }

        th:hover {
            background: #5568d3;
        }

        th.sortable::after {
            content: ' ↕';
            opacity: 0.5;
            font-size: 0.8em;
        }

        th.sort-asc::after {
            content: ' ↑';
            opacity: 1;
        }

        th.sort-desc::after {
            content: ' ↓';
            opacity: 1;
        }

        td {
            padding: 15px;
            border-bottom: 1px solid #e0e0e0;
        }

        tr:hover {
            background: #f8f9fa;
        }

        .badge {
            display: inline-block;
            padding: 4px 10px;
            border-radius: 12px;
            font-size: 0.85em;
            font-weight: 600;
        }

        .badge-zone {
            background: #e3f2fd;
            color: #1976d2;
        }

        .badge-yes {
            background: #c8e6c9;
            color: #2e7d32;
        }

        .badge-no {
            background: #ffcdd2;
            color: #c62828;
        }

        .badge-sector {
            background: #f3e5f5;
            color: #7b1fa2;
        }

        a {
            color: #667eea;
            text-decoration: none;
        }

        a:hover {
            text-decoration: underline;
        }

        .no-results {
            text-align: center;
            padding: 60px 20px;
            color: #666;
        }

        .no-results h2 {
            margin-bottom: 10px;
            color: #333;
        }

        @media (max-width: 768px) {
            .header h1 {
                font-size: 1.8em;
            }

            .stats {
                grid-template-columns: repeat(2, 1fr);
            }

            table {
                font-size: 0.9em;
            }

            th, td {
                padding: 10px 8px;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🏘️ FHCQ Cooperatives</h1>
            <p>Liste des coopératives d'habitation</p>
        </div>

        <div class="stats">
            <div class="stat-card">
                <div class="number"><?php echo number_format($stats['total']); ?></div>
                <div class="label">Total des coopératives</div>
            </div>
            <div class="stat-card">
                <div class="number"><?php echo $stats['zones']; ?></div>
                <div class="label">Zones</div>
            </div>
            <div class="stat-card">
                <div class="number"><?php echo $stats['sectors']; ?></div>
                <div class="label">Secteurs</div>
            </div>
        </div>

        <div class="filters">
            <form method="GET" action="">
                <div class="filter-group">
                    <label for="zone">Zone</label>
                    <select name="zone" id="zone">
                        <option value="">Toutes les zones</option>
                        <?php foreach ($zones as $zone): ?>
                            <option value="<?php echo $zone; ?>" <?php echo $zone_filter == $zone ? 'selected' : ''; ?>>
                                Zone <?php echo $zone; ?>
                            </option>
                        <?php endforeach; ?>
                    </select>
                </div>

                <div class="filter-group">
                    <label for="sector">Secteur</label>
                    <select name="sector" id="sector">
                        <option value="">Tous les secteurs</option>
                        <?php foreach ($sectors as $sector): ?>
                            <option value="<?php echo htmlspecialchars($sector); ?>" <?php echo $sector_filter === $sector ? 'selected' : ''; ?>>
                                <?php echo htmlspecialchars($sector); ?>
                            </option>
                        <?php endforeach; ?>
                    </select>
                </div>

                <div class="filter-group">
                    <label for="dwelling">Type de logement</label>
                    <select name="dwelling" id="dwelling">
                        <option value="">Tous les types</option>
                        <option value="5" <?php echo $dwelling_filter == 5 ? 'selected' : ''; ?>>5½</option>
                        <option value="6" <?php echo $dwelling_filter == 6 ? 'selected' : ''; ?>>6½</option>
                        <option value="7" <?php echo $dwelling_filter == 7 ? 'selected' : ''; ?>>7½</option>
                    </select>
                </div>

                <div class="filter-group">
                    <button type="submit" class="btn">Filtrer</button>
                    <a href="?" class="btn btn-secondary" style="margin-top: 10px; display: block; text-align: center;">Réinitialiser</a>
                </div>
            </form>
        </div>

        <div class="table-container">
            <?php if (count($listings) > 0): ?>
                <table>
                    <thead>
                        <tr>
                            <th class="sortable <?php echo $sort === 'name' ? 'sort-' . strtolower($order) : ''; ?>" 
                                onclick="sortTable('name')">Nom</th>
                            <th class="sortable <?php echo $sort === 'address' ? 'sort-' . strtolower($order) : ''; ?>" 
                                onclick="sortTable('address')">Adresse</th>
                            <th>Contact</th>
                            <th class="sortable <?php echo $sort === 'zone' ? 'sort-' . strtolower($order) : ''; ?>" 
                                onclick="sortTable('zone')">Zone</th>
                            <th class="sortable <?php echo $sort === 'sector' ? 'sort-' . strtolower($order) : ''; ?>" 
                                onclick="sortTable('sector')">Secteur</th>
                            <th class="sortable <?php echo $sort === 'dwelling_type' ? 'sort-' . strtolower($order) : ''; ?>" 
                                onclick="sortTable('dwelling_type')">Type</th>
                            <th>Lien</th>
                        </tr>
                    </thead>
                    <tbody>
                        <?php foreach ($listings as $listing): ?>
                            <tr>
                                <td><strong><?php echo htmlspecialchars($listing['name']); ?></strong></td>
                                <td><?php echo htmlspecialchars($listing['address']); ?></td>
                                <td>
                                    <?php if ($listing['email']): ?>
                                        <a href="mailto:<?php echo htmlspecialchars($listing['email']); ?>">
                                            <?php echo htmlspecialchars($listing['email']); ?>
                                        </a><br>
                                    <?php endif; ?>
                                    <?php if ($listing['phone']): ?>
                                        <a href="tel:<?php echo htmlspecialchars($listing['phone']); ?>">
                                            <?php echo htmlspecialchars($listing['phone']); ?>
                                        </a>
                                    <?php endif; ?>
                                    <?php if (!$listing['email'] && !$listing['phone']): ?>
                                        <span style="color: #999;">N/A</span>
                                    <?php endif; ?>
                                </td>
                                <td>
                                    <?php if ($listing['zone']): ?>
                                        <span class="badge badge-zone">Zone <?php echo $listing['zone']; ?></span>
                                    <?php else: ?>
                                        <span style="color: #999;">-</span>
                                    <?php endif; ?>
                                </td>
                                <td>
                                    <span class="badge badge-sector"><?php echo htmlspecialchars($listing['sector']); ?></span>
                                </td>
                                <td><?php echo $listing['dwelling_type']; ?>½</td>
                                <td>
                                    <a href="<?php echo htmlspecialchars($listing['url']); ?>" target="_blank">
                                        Voir →
                                    </a>
                                </td>
                            </tr>
                        <?php endforeach; ?>
                    </tbody>
                </table>
            <?php else: ?>
                <div class="no-results">
                    <h2>Aucun résultat trouvé</h2>
                    <p>Essayez de modifier vos filtres de recherche.</p>
                </div>
            <?php endif; ?>
        </div>
    </div>

    <script>
        function sortTable(column) {
            const url = new URL(window.location);
            const currentSort = url.searchParams.get('sort');
            const currentOrder = url.searchParams.get('order');
            
            if (currentSort === column && currentOrder === 'ASC') {
                url.searchParams.set('order', 'DESC');
            } else {
                url.searchParams.set('order', 'ASC');
            }
            
            url.searchParams.set('sort', column);
            window.location = url.toString();
        }
    </script>
</body>
</html>

