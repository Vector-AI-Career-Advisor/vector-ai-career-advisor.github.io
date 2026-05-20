import api from './client'

export interface Application {
  application_id: number
  status: 'applied' | 'screening' | 'interview' | 'offer' | 'rejected' | 'withdrawn'
  applied_at: string
  updated_at: string
  notes: string | null
  job_id: string
  title: string
  company: string
  location: string
  url: string
  role: string | null
  seniority: string | null
  logo_url: string | null
}

export async function fetchApplications(status?: string): Promise<Application[]> {
  const params = status ? { status } : {}
  const res = await api.get<Application[]>('/applications/', { params })
  return res.data
}

export async function createApplication(jobId: string): Promise<void> {
  await api.post('/applications/', { job_id: jobId })
}

export async function updateApplicationStatus(
  jobId: string,
  status: Application['status'],
): Promise<void> {
  await api.patch(`/applications/${jobId}`, { status })
}
