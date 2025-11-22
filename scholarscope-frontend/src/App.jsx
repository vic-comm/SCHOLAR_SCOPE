import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import HomePage from "./pages/Home";
import ScholarshipDetail from "./pages/ScholarshipDetail";

export default function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/scholarships/:id" element={<ScholarshipDetail />} />
      </Routes>
    </Router>
  );
}
