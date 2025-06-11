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

  const updateVehicleStatus = async (vehicleId, status) => {
    try {
      await axios.put(`${API}/vehicles/${vehicleId}`, { status });
      // Reload deals to reflect changes
      loadDeals();
    } catch (error) {
      console.error("Error updating vehicle:", error);
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
    const profitColor = vehicle.est_profit > 0 ? 'text-green-600' : 'text-red-600';
    const roiColor = vehicle.roi_percent > 0 ? 'text-green-600' : 'text-red-600';

    return (
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 hover:shadow-md transition-shadow">
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
                {vehicle.mileage?.toLocaleString()} mi
              </span>
              <span className="flex items-center">
                <MapPin className="h-4 w-4 mr-1" />
                {vehicle.location}
              </span>
            </div>
          </div>
          <div className="text-right">
            <div className="flex items-center space-x-1">
              <span className="text-xs bg-blue-100 text-blue-800 px-2 py-1 rounded-full">
                {vehicle.source.replace('_', '.')}
              </span>
            </div>
            <p className="text-xs text-gray-500 mt-1">{vehicle.seller_type}</p>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4 mb-4">
          <div>
            <p className="text-sm text-gray-500">Asking Price</p>
            <p className="text-xl font-bold text-gray-900">{formatCurrency(vehicle.asking_price)}</p>
          </div>
          <div>
            <p className="text-sm text-gray-500">Market Value</p>
            <p className="text-xl font-bold text-gray-700">{formatCurrency(vehicle.market_value)}</p>
          </div>
        </div>

        <div className="grid grid-cols-3 gap-4 mb-4 p-3 bg-gray-50 rounded-lg">
          <div className="text-center">
            <p className="text-xs text-gray-500">Est. Profit</p>
            <p className={`text-lg font-bold ${profitColor}`}>
              {formatCurrency(vehicle.est_profit)}
            </p>
          </div>
          <div className="text-center">
            <p className="text-xs text-gray-500">ROI</p>
            <p className={`text-lg font-bold ${roiColor}`}>
              {formatPercent(vehicle.roi_percent)}
            </p>
          </div>
          <div className="text-center">
            <p className="text-xs text-gray-500">Flip Score</p>
            <p className="text-lg font-bold text-blue-600">{vehicle.flip_score}/10</p>
          </div>
        </div>

        <div className="flex justify-between items-center">
          <span className={`px-3 py-1 rounded-full text-xs font-medium ${getStatusColor(vehicle.status)}`}>
            {vehicle.status.replace('_', ' ')}
          </span>
          <div className="flex space-x-2">
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
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-6">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">FlipBot AI 🚗</h1>
              <p className="text-gray-600">Premium Vehicle Resale Intelligence</p>
            </div>
            <div className="flex items-center space-x-4">
              <div className="text-right">
                <p className="text-sm text-gray-500">Deal Opportunities</p>
                <p className="text-2xl font-bold text-green-600">{stats.deal_opportunities || 0}</p>
              </div>
              <div className="text-right">
                <p className="text-sm text-gray-500">Total Vehicles</p>
                <p className="text-2xl font-bold text-blue-600">{stats.total_vehicles || 0}</p>
              </div>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Search Section */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 mb-8">
          <div className="flex items-center space-x-4 mb-4">
            <div className="flex-1 flex">
              <input
                type="text"
                placeholder="Search make, model, or trim (e.g., Porsche 911, BMW M3)"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
                className="flex-1 px-4 py-3 border border-gray-300 rounded-l-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
              <button
                onClick={handleSearch}
                className="px-6 py-3 bg-blue-600 text-white rounded-r-lg hover:bg-blue-700 transition-colors flex items-center"
              >
                <Search className="h-5 w-5" />
              </button>
            </div>
            <button
              onClick={() => setShowFilters(!showFilters)}
              className="px-4 py-3 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors flex items-center space-x-2"
            >
              <Filter className="h-5 w-5" />
              <span>Filters</span>
            </button>
          </div>

          {/* Filters */}
          {showFilters && (
            <div className="grid grid-cols-1 md:grid-cols-5 gap-4 mt-4 p-4 bg-gray-50 rounded-lg">
              <input
                type="text"
                placeholder="Zip Code"
                value={filters.zipCode}
                onChange={(e) => setFilters({...filters, zipCode: e.target.value})}
                className="px-3 py-2 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              <select
                value={filters.distance}
                onChange={(e) => setFilters({...filters, distance: e.target.value})}
                className="px-3 py-2 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
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
                className="px-3 py-2 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              <input
                type="number"
                placeholder="Min Year"
                value={filters.yearMin}
                onChange={(e) => setFilters({...filters, yearMin: e.target.value})}
                className="px-3 py-2 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              <input
                type="number"
                placeholder="Min Profit"
                value={filters.minProfit}
                onChange={(e) => setFilters({...filters, minProfit: e.target.value})}
                className="px-3 py-2 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          )}
        </div>

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
              Deal Opportunities
            </h2>
            <button
              onClick={loadDeals}
              className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors text-sm"
            >
              Refresh Deals
            </button>
          </div>

          {loading ? (
            <div className="text-center py-12">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
              <p className="text-gray-600 mt-4">Loading vehicles...</p>
            </div>
          ) : vehicles.length === 0 ? (
            <div className="text-center py-12">
              <Car className="h-16 w-16 text-gray-400 mx-auto mb-4" />
              <p className="text-gray-600">No vehicles found. Try adjusting your search or filters.</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {vehicles.map((vehicle) => (
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
