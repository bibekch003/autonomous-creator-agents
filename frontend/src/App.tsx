import { Navigate, Route, Routes } from 'react-router-dom'
import { Layout } from './components/Layout'
import { RedirectIfAuthed, RequireAuth } from './components/RequireAuth'
import Landing from './pages/Landing'
import Login from './pages/Login'
import Register from './pages/Register'
import Dashboard from './pages/Dashboard'
import Projects from './pages/Projects'
import VideoStudio from './pages/VideoStudio'
import ClipGenerator from './pages/ClipGenerator'
import ThumbnailStudio from './pages/ThumbnailStudio'
import ContentManager from './pages/ContentManager'
import Agents from './pages/Agents'
import Analytics from './pages/Analytics'
import SettingsPage from './pages/Settings'

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Landing />} />
      <Route path="/login" element={<RedirectIfAuthed><Login /></RedirectIfAuthed>} />
      <Route path="/register" element={<RedirectIfAuthed><Register /></RedirectIfAuthed>} />

      <Route path="/app" element={<RequireAuth><Layout /></RequireAuth>}>
        <Route index element={<Navigate to="/app/dashboard" replace />} />
        <Route path="dashboard" element={<Dashboard />} />
        <Route path="projects" element={<Projects />} />
        <Route path="videos/:videoId" element={<VideoStudio />} />
        <Route path="videos/:videoId/clips" element={<ClipGenerator />} />
        <Route path="videos/:videoId/thumbnails" element={<ThumbnailStudio />} />
        <Route path="videos/:videoId/content" element={<ContentManager />} />
        <Route path="agents" element={<Agents />} />
        <Route path="analytics" element={<Analytics />} />
        <Route path="settings" element={<SettingsPage />} />
      </Route>

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
