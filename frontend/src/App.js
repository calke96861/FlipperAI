import { useState, useEffect } from "react";
import "./App.css";
import axios from "axios";
import { 
  Search, 
  ArrowUpRight, 
  ArrowDownRight, 
  Car, 
  DollarSign, 
  TrendingUp,
  MapPin,
  Calendar,
  Filter,
  Eye,
  MessageCircle,
  CheckCircle,
  X
} from "lucide-react";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

function App() {
  const [vehicles, setVehicles] = useState([]);
  const [trending, setTrending] = useState([]);
  const [stats, setStats] = useState({});
  const [searchQuery, setSearchQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [filters, setFilters] = useState({
    zipCode: "",
    distance: "",
    priceMax: "",
    yearMin: "",
    minProfit: ""
  });
  const [showFilters, setShowFilters] = useState(false);
  const [scrapingStatus, setScrapingStatus] = useState(null);
  const [scrapingLoading, setScrapingLoading] = useState(false);
  const [sortBy, setSortBy] = useState("flip_score");
  const [sortOrder, setSortOrder] = useState("desc");
  const [viewMode, setViewMode] = useState("grid");
  const [savedVehicles, setSavedVehicles] = useState(new Set());

  // Load initial data
  useEffect(() => {
    loadDeals();
    loadTrending();
    loadStats();
  }, []);

  const loadDeals = async () => {
    try {
      setLoading(true);
      const response = await axios.get(`${API}/deals?limit=20`);
      setVehicles(response.data);
    } catch (error) {
      console.error("Error loading deals:", error);
    } finally {
      setLoading(false);
    }
  };

  const loadTrending = async () => {
    try {
      const response = await axios.get(`${API}/trending`);
      setTrending(response.data);
    } catch (error) {
      console.error("Error loading trending:", error);
    }
  };

  const loadStats = async () => {
    try {
      const response = await axios.get(`${API}/stats`);
      setStats(response.data);
    } catch (error) {
      console.error("Error loading stats:", error);
    }
  };

  const handleSearch = async () => {
    if (!searchQuery.trim()) {
      loadDeals();
      return;
    }

    try {
      setLoading(true);
      let url = `${API}/search?q=${encodeURIComponent(searchQuery)}`;
      
      if (filters.zipCode) url += `&zip_code=${filters.zipCode}`;
      if (filters.distance) url += `&distance=${filters.distance}`;
      if (filters.priceMax) url += `&price_max=${filters.priceMax}`;
      if (filters.yearMin) url += `&year_min=${filters.yearMin}`;

      const response = await axios.get(url);
      setVehicles(response.data);
    } catch (error) {
      console.error("Error searching:", error);
    } finally {
      setLoading(false);
    }
  };

  const sortVehicles = (vehicleList) => {
    return [...vehicleList].sort((a, b) => {
      let aVal = a[sortBy];
      let bVal = b[sortBy];
      
      // Handle null/undefined values
      if (aVal == null && bVal == null) return 0;
      if (aVal == null) return sortOrder === "desc" ? 1 : -1;
      if (bVal == null) return sortOrder === "desc" ? -1 : 1;
      
      // Convert to numbers for numeric fields
      if (sortBy === "asking_price" || sortBy === "est_profit" || sortBy === "roi_percent" || sortBy === "flip_score" || sortBy === "year" || sortBy === "mileage") {
        aVal = parseFloat(aVal) || 0;
        bVal = parseFloat(bVal) || 0;
      }
      
      if (sortOrder === "desc") {
        return bVal - aVal;
      } else {
        return aVal - bVal;
      }
    });
  };

  const filterVehicles = (vehicleList) => {
    return vehicleList.filter(vehicle => {
      if (filters.priceMax && vehicle.asking_price > parseFloat(filters.priceMax)) return false;
      if (filters.yearMin && vehicle.year < parseInt(filters.yearMin)) return false;
      if (filters.minProfit && (vehicle.est_profit || 0) < parseFloat(filters.minProfit)) return false;
      return true;
    });
  };

  const toggleSaveVehicle = (vehicleId) => {
    const newSaved = new Set(savedVehicles);
    if (newSaved.has(vehicleId)) {
      newSaved.delete(vehicleId);
    } else {
      newSaved.add(vehicleId);
    }
    setSavedVehicles(newSaved);
    localStorage.setItem('savedVehicles', JSON.stringify([...newSaved]));
  };

  // Load saved vehicles from localStorage
  useEffect(() => {
    const saved = localStorage.getItem('savedVehicles');
    if (saved) {
      setSavedVehicles(new Set(JSON.parse(saved)));
    }
  }, []);

  // Apply sorting and filtering to vehicles
  const processedVehicles = sortVehicles(filterVehicles(vehicles));

  const updateVehicleStatus = async (vehicleId, status) => {
    try {
      await axios.put(`${API}/vehicles/${vehicleId}`, { status });
      // Reload deals to reflect changes
      loadDeals();
    } catch (error) {
      console.error("Error updating vehicle:", error);
    }
  };

  const handleScrape = async () => {
    if (!searchQuery.trim()) return;

    try {
      setScrapingLoading(true);
      setScrapingStatus("Scraping live listings...");
      
      const response = await axios.post(`${API}/scrape/quick`, null, {
        params: {
          query: searchQuery,
          location: filters.zipCode || "",
          max_results: 15
        }
      });
      
      setScrapingStatus(`Found ${response.data.vehicles_found} live vehicles in ${response.data.duration.toFixed(1)}s`);
      
      // Add scraped vehicles to current results
      if (response.data.vehicles && response.data.vehicles.length > 0) {
        const scrapedVehicles = response.data.vehicles.map(v => ({
          ...v,
          seller_type: v.seller_type || 'unknown',
          source: v.source || 'unknown',
          status: v.status || 'new'
        }));
        // Show only scraped results for better UX
        setVehicles(scrapedVehicles);
      } else {
        setVehicles([]);
      }
      
    } catch (error) {
      console.error("Error scraping:", error);
      setScrapingStatus("Scraping failed. Please try again.");
    } finally {
      setScrapingLoading(false);
      setTimeout(() => setScrapingStatus(null), 5000);
    }
  };

  const testScrapers = async () => {
    try {
      const response = await axios.get(`${API}/scrape/test`);
      console.log("Scraper status:", response.data);
      
      const workingScrapers = Object.entries(response.data)
        .filter(([source, working]) => working)
        .map(([source]) => source);
      
      if (workingScrapers.length > 0) {
        setScrapingStatus(`Working scrapers: ${workingScrapers.join(', ')}`);
      } else {
        setScrapingStatus("No scrapers are currently working");
      }
      
      setTimeout(() => setScrapingStatus(null), 5000);
    } catch (error) {
      console.error("Error testing scrapers:", error);
    }
  };

  const formatCurrency = (amount) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0
    }).format(amount);
  };

  const formatPercent = (percent) => {
    return `${percent?.toFixed(1)}%`;
  };

  const getStatusColor = (status) => {
    const colors = {
      new: "bg-blue-100 text-blue-800",
      watching: "bg-yellow-100 text-yellow-800",
      contacted: "bg-purple-100 text-purple-800",
      negotiating: "bg-orange-100 text-orange-800",
      purchased: "bg-green-100 text-green-800",
      passed: "bg-gray-100 text-gray-800"
    };
    return colors[status] || colors.new;
  };

  const TrendingTile = ({ trend }) => {
    const isUp = trend.price_change_percent >= 0;
    const Icon = isUp ? ArrowUpRight : ArrowDownRight;
    
    return (
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 hover:shadow-md transition-shadow">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className={`p-2 rounded-full ${isUp ? 'bg-green-100' : 'bg-red-100'}`}>
              <Icon className={`h-5 w-5 ${isUp ? 'text-green-600' : 'text-red-600'}`} />
            </div>
            <div>
              <p className="text-sm font-medium text-gray-900">{trend.make_model}</p>
              <p className="text-xs text-gray-500">{trend.total_listings} listings</p>
            </div>
          </div>
          <div className="text-right">
            <p className={`text-lg font-semibold ${isUp ? 'text-green-600' : 'text-red-600'}`}>
              {formatPercent(trend.price_change_percent)}
            </p>
            <p className="text-sm text-gray-500">{formatCurrency(trend.avg_price)}</p>
          </div>
        </div>
      </div>
    );
  };

  const VehicleCard = ({ vehicle }) => {
    const profitColor = (vehicle.est_profit || 0) > 0 ? 'text-green-600' : 'text-red-600';
    const roiColor = (vehicle.roi_percent || 0) > 0 ? 'text-green-600' : 'text-red-600';
    const isSaved = savedVehicles.has(vehicle.id);

    return (
      <div className={`bg-white rounded-lg shadow-sm border border-gray-200 p-6 hover:shadow-md transition-shadow ${isSaved ? 'ring-2 ring-yellow-400' : ''}`}>
        <div className="flex justify-between items-start mb-4">
          <div>
            <h3 className="text-lg font-semibold text-gray-900">
              {vehicle.year} {vehicle.make} {vehicle.model}
            </h3>
            {vehicle.trim && (
              <p className="text-sm text-gray-600">{vehicle.trim}</p>
            )}
            <div className="flex items-center space-x-4 mt-2 text-sm text-gray-500">
              <span className="flex items-center">
                <Car className="h-4 w-4 mr-1" />
                {vehicle.mileage ? vehicle.mileage.toLocaleString() : 'N/A'} mi
              </span>
              <span className="flex items-center">
                <MapPin className="h-4 w-4 mr-1" />
                {vehicle.location || 'Unknown'}
              </span>
            </div>
          </div>
          <div className="text-right">
            <div className="flex items-center space-x-1 mb-2">
              <span className="text-xs bg-blue-100 text-blue-800 px-2 py-1 rounded-full">
                {vehicle.source ? vehicle.source.replace('_', '.') : 'unknown'}
              </span>
              {(vehicle.flip_score || 0) >= 5 && (
                <span className="text-xs bg-green-100 text-green-800 px-2 py-1 rounded-full">
                  🔥 Hot Deal
                </span>
              )}
            </div>
            <p className="text-xs text-gray-500">{vehicle.seller_type || 'unknown'}</p>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4 mb-4">
          <div>
            <p className="text-sm text-gray-500">Asking Price</p>
            <p className="text-xl font-bold text-gray-900">{formatCurrency(vehicle.asking_price || 0)}</p>
          </div>
          <div>
            <p className="text-sm text-gray-500">Market Value</p>
            <p className="text-xl font-bold text-gray-700">{formatCurrency(vehicle.market_value || 0)}</p>
          </div>
        </div>

        <div className="grid grid-cols-3 gap-4 mb-4 p-3 bg-gray-50 rounded-lg">
          <div className="text-center">
            <p className="text-xs text-gray-500">Est. Profit</p>
            <p className={`text-lg font-bold ${profitColor}`}>
              {formatCurrency(vehicle.est_profit || 0)}
            </p>
          </div>
          <div className="text-center">
            <p className="text-xs text-gray-500">ROI</p>
            <p className={`text-lg font-bold ${roiColor}`}>
              {formatPercent(vehicle.roi_percent || 0)}
            </p>
          </div>
          <div className="text-center">
            <p className="text-xs text-gray-500">Flip Score</p>
            <div className="flex items-center justify-center">
              <p className="text-lg font-bold text-blue-600">{vehicle.flip_score || 0}/10</p>
              {(vehicle.flip_score || 0) >= 7 && <span className="ml-1 text-red-500">🔥</span>}
            </div>
          </div>
        </div>

        <div className="flex justify-between items-center">
          <span className={`px-3 py-1 rounded-full text-xs font-medium ${getStatusColor(vehicle.status)}`}>
            {(vehicle.status || 'new').replace('_', ' ')}
          </span>
          <div className="flex space-x-2">
            <button
              onClick={() => toggleSaveVehicle(vehicle.id)}
              className={`p-2 ${isSaved ? 'text-yellow-600' : 'text-gray-400'} hover:text-yellow-600 transition-colors`}
              title={isSaved ? "Remove from Saved" : "Save Vehicle"}
            >
              {isSaved ? <CheckCircle className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
            </button>
            <button
              onClick={() => updateVehicleStatus(vehicle.id, 'watching')}
              className="p-2 text-gray-400 hover:text-blue-600 transition-colors"
              title="Watch"
            >
              <Eye className="h-4 w-4" />
            </button>
            <button
              onClick={() => updateVehicleStatus(vehicle.id, 'contacted')}
              className="p-2 text-gray-400 hover:text-green-600 transition-colors"
              title="Contact"
            >
              <MessageCircle className="h-4 w-4" />
            </button>
            <button
              onClick={() => window.open(vehicle.url, '_blank')}
              className="px-3 py-1 bg-blue-600 text-white text-xs rounded hover:bg-blue-700 transition-colors"
            >
              View Listing
            </button>
          </div>
        </div>
      </div>
    );
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 via-white to-gray-50">
      {/* Header */}
      <header className="bg-white/80 backdrop-blur-sm border-b border-gray-200 sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-6 py-6">
          <div className="flex justify-between items-center">
            <div>
              <h1 className="heading-display text-gray-900">FlipBot AI</h1>
              <p className="body-large text-gray-600 mt-1">Professional Vehicle Intelligence Platform</p>
            </div>
            <div className="flex items-center space-x-8">
              <div className="text-center">
                <div className="pill pill-success mb-2">
                  <span className="body-small">Deal Opportunities</span>
                </div>
                <p className="heading-3 text-secondary-600">{stats.deal_opportunities || 0}</p>
              </div>
              <div className="text-center">
                <div className="pill pill-primary mb-2">
                  <span className="body-small">Total Vehicles</span>
                </div>
                <p className="heading-3 text-primary-600">{stats.total_vehicles || 0}</p>
              </div>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-12">
        {/* Hero Search Section */}
        <section className="relative mb-16">
          <div className="absolute inset-0 bg-gradient-to-r from-primary-50 to-secondary-50 rounded-3xl -z-10"></div>
          <div className="card-elevated bg-white/90 backdrop-blur-sm p-8 rounded-3xl">
            <div className="text-center mb-8">
              <h2 className="heading-2 text-gray-900 mb-3">Discover Your Next Profitable Vehicle</h2>
              <p className="body-large text-gray-600">Search across multiple sources or scrape live listings in real-time</p>
            </div>
            
            <div className="flex flex-col lg:flex-row items-center space-y-4 lg:space-y-0 lg:space-x-4 mb-6">
              <div className="flex-1 w-full flex">
                <input
                  type="text"
                  placeholder="Search: BMW M3, Porsche 911, RAM TRX, 2021 Tesla Model S"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
                  className="form-input rounded-r-none text-base"
                />
                <button
                  onClick={handleSearch}
                  className="btn-secondary rounded-l-none border-l-0 flex items-center justify-center min-w-[60px]"
                  title="Search Database"
                >
                  <Search className="h-5 w-5" />
                </button>
                <button
                  onClick={handleScrape}
                  disabled={scrapingLoading || !searchQuery.trim()}
                  className="btn-success rounded-l-none border-l-0 flex items-center justify-center min-w-[60px] disabled:opacity-50"
                  title="Live Scrape from dealer websites"
                >
                  {scrapingLoading ? (
                    <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white"></div>
                  ) : (
                    <TrendingUp className="h-5 w-5" />
                  )}
                </button>
              </div>
              
              <div className="flex space-x-3">
                <button
                  onClick={() => setShowFilters(!showFilters)}
                  className="btn-secondary flex items-center space-x-2"
                >
                  <Filter className="h-4 w-4" />
                  <span className="body-small">Filters</span>
                </button>
                <button
                  onClick={testScrapers}
                  className="btn-secondary flex items-center space-x-2"
                  title="Test Scrapers"
                >
                  <CheckCircle className="h-4 w-4" />
                  <span className="body-small">Test</span>
                </button>
              </div>
            </div>

            {/* Search Status */}
            {scrapingStatus && (
              <div className="mb-6 p-4 bg-blue-50 border border-blue-200 rounded-xl">
                <p className="body-base text-blue-800">{scrapingStatus}</p>
              </div>
            )}

            {/* Quick Filter Pills */}
            <div className="flex flex-wrap gap-3 justify-center">
              <button
                onClick={() => { setSortBy("est_profit"); setSortOrder("desc"); }}
                className="pill pill-success hover:scale-105 cursor-pointer transition-transform"
              >
                💰 High Profit
              </button>
              <button
                onClick={() => { setSortBy("roi_percent"); setSortOrder("desc"); }}
                className="pill pill-primary hover:scale-105 cursor-pointer transition-transform"
              >
                📈 High ROI
              </button>
              <button
                onClick={() => { setFilters({...filters, priceMax: "50000"}); setTimeout(() => setFilters(prev => ({...prev})), 10); }}
                className="pill pill-accent hover:scale-105 cursor-pointer transition-transform"
              >
                💵 Under $50K
              </button>
              <button
                onClick={() => { setSortBy("mileage"); setSortOrder("asc"); }}
                className="pill pill-warning hover:scale-105 cursor-pointer transition-transform"
              >
                🏃 Low Mileage
              </button>
              <button
                onClick={() => { setSortBy("year"); setSortOrder("desc"); }}
                className="pill pill-success hover:scale-105 cursor-pointer transition-transform"
              >
                ⚡ Newest
              </button>
            </div>

            {/* Advanced Filters */}
            {showFilters && (
              <div className="mt-8 p-6 bg-gray-50 rounded-xl">
                <h3 className="heading-3 text-gray-900 mb-4">Advanced Filters</h3>
                <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-5 gap-4">
                  <input
                    type="text"
                    placeholder="Zip Code"
                    value={filters.zipCode}
                    onChange={(e) => setFilters({...filters, zipCode: e.target.value})}
                    className="form-input"
                  />
                  <select
                    value={filters.distance}
                    onChange={(e) => setFilters({...filters, distance: e.target.value})}
                    className="form-select"
                  >
                    <option value="">Distance</option>
                    <option value="25">25 miles</option>
                    <option value="50">50 miles</option>
                    <option value="100">100 miles</option>
                    <option value="250">250 miles</option>
                    <option value="500">500 miles</option>
                  </select>
                  <input
                    type="number"
                    placeholder="Max Price"
                    value={filters.priceMax}
                    onChange={(e) => setFilters({...filters, priceMax: e.target.value})}
                    className="form-input"
                  />
                  <input
                    type="number"
                    placeholder="Min Year"
                    value={filters.yearMin}
                    onChange={(e) => setFilters({...filters, yearMin: e.target.value})}
                    className="form-input"
                  />
                  <input
                    type="number"
                    placeholder="Min Profit"
                    value={filters.minProfit}
                    onChange={(e) => setFilters({...filters, minProfit: e.target.value})}
                    className="form-input"
                  />
                </div>
              </div>
            )}
          </div>
        </section>

        {/* Trending Section */}
        <div className="mb-8">
          <h2 className="text-2xl font-bold text-gray-900 mb-6 flex items-center">
            <TrendingUp className="h-6 w-6 mr-2" />
            Market Trends
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {trending.map((trend, index) => (
              <TrendingTile key={index} trend={trend} />
            ))}
          </div>
        </div>

        {/* Deals Section */}
        <div>
          <div className="flex justify-between items-center mb-6">
            <h2 className="text-2xl font-bold text-gray-900 flex items-center">
              <DollarSign className="h-6 w-6 mr-2" />
              Deal Opportunities ({processedVehicles.length})
            </h2>
            <div className="flex items-center space-x-4">
              {/* Sort Dropdown */}
              <select
                value={`${sortBy}-${sortOrder}`}
                onChange={(e) => {
                  const [field, order] = e.target.value.split('-');
                  setSortBy(field);
                  setSortOrder(order);
                }}
                className="px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
              >
                <option value="flip_score-desc">🎯 Best Flip Score</option>
                <option value="est_profit-desc">💰 Highest Profit</option>
                <option value="roi_percent-desc">📈 Highest ROI</option>
                <option value="asking_price-asc">💵 Lowest Price</option>
                <option value="asking_price-desc">💎 Highest Price</option>
                <option value="year-desc">⚡ Newest Year</option>
                <option value="year-asc">🏛️ Oldest Year</option>
                <option value="mileage-asc">🏃 Lowest Mileage</option>
                <option value="mileage-desc">🛣️ Highest Mileage</option>
              </select>
              
              {/* View Toggle */}
              <div className="flex border border-gray-300 rounded-lg">
                <button
                  onClick={() => setViewMode("grid")}
                  className={`px-3 py-2 text-sm ${viewMode === "grid" ? "bg-blue-600 text-white" : "bg-white text-gray-700"} rounded-l-lg transition-colors`}
                >
                  Grid
                </button>
                <button
                  onClick={() => setViewMode("list")}
                  className={`px-3 py-2 text-sm ${viewMode === "list" ? "bg-blue-600 text-white" : "bg-white text-gray-700"} rounded-r-lg transition-colors`}
                >
                  List
                </button>
              </div>
              
              <button
                onClick={loadDeals}
                className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors text-sm"
              >
                Refresh Deals
              </button>
            </div>
          </div>

          {loading ? (
            <div className="text-center py-12">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
              <p className="text-gray-600 mt-4">Loading vehicles...</p>
            </div>
          ) : processedVehicles.length === 0 ? (
            <div className="text-center py-12">
              <Car className="h-16 w-16 text-gray-400 mx-auto mb-4" />
              <p className="text-gray-600">No vehicles found. Try adjusting your search or filters.</p>
            </div>
          ) : (
            <div className={viewMode === "grid" ? "grid grid-cols-1 lg:grid-cols-2 gap-6" : "space-y-4"}>
              {processedVehicles.map((vehicle) => (
                <VehicleCard key={vehicle.id} vehicle={vehicle} />
              ))}
            </div>
          )}
        </div>
      </main>
    </div>
  );
}

export default App;
