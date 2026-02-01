/**
 * SOAC Frontend App
 */

import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './auth/AuthContext';
import { ProtectedRoute } from './auth/ProtectedRoute';
import { LoginPage } from './pages/LoginPage';
import { RegisterPage } from './pages/RegisterPage';
import { RegisteredPage } from './pages/RegisteredPage';
import { LandingPage } from './pages/LandingPage';
import { DocsPage } from './pages/DocsPage';
import { DashboardPage } from './pages/DashboardPage';
import { NewJobPage } from './pages/NewJobPage';
import { JobDetailPage } from './pages/JobDetailPage';
import { ThemeProvider } from './theme/ThemeContext';
import { MascotProvider } from './mascot/MascotContext';
import { BrutalShell } from './brutal/BrutalShell';
import './index.css';

function App() {
  return (
    <ThemeProvider>
      <AuthProvider>
        <BrowserRouter>
          <MascotProvider>
            <BrutalShell>
              <div className="relative min-h-screen">
                <div className="relative z-10 min-h-screen">
                  <Routes>
                    <Route path="/login" element={<LoginPage />} />
                    <Route path="/register" element={<RegisterPage />} />
                    <Route path="/registered" element={<RegisteredPage />} />

                    <Route path="/" element={<LandingPage />} />
                    <Route path="/docs" element={<DocsPage />} />
                    <Route
                      path="/dashboard"
                      element={
                        <ProtectedRoute>
                          <DashboardPage />
                        </ProtectedRoute>
                      }
                    />
                    <Route
                      path="/new"
                      element={
                        <ProtectedRoute>
                          <NewJobPage />
                        </ProtectedRoute>
                      }
                    />
                    <Route
                      path="/jobs/:jobId"
                      element={
                        <ProtectedRoute>
                          <JobDetailPage />
                        </ProtectedRoute>
                      }
                    />

                    <Route path="*" element={<Navigate to="/" replace />} />
                  </Routes>
                </div>
              </div>
            </BrutalShell>
          </MascotProvider>
        </BrowserRouter>
      </AuthProvider>
    </ThemeProvider>
  );
}

export default App;
