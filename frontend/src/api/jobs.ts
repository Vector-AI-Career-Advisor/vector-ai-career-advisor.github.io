import api from './client'

export interface Job {
  id: string
  title?: string
  role?: string
  seniority?: string
  company?: string
  location?: string
  url?: string
  description?: string
  skills_must?: string[]
  skills_nice?: string[]
  yearsexperience?: number
  past_experience?: string[]
  keyword?: string
  source?: string
  posted_at?: string
  scraped_at?: string
  
}

export interface JobFilters {
  keyword?: string
  seniority?: string
  location?: string
  limit?: number
  offset?: number
}

export interface JobsResponse {
  items: Job[]
  total: number
}

export const fetchJobs = async (filters: JobFilters = {}): Promise<JobsResponse> => {
  const { data } = await api.get('/jobs/', { params: filters })
  return data
}

export const fetchJob = async (id: string): Promise<Job> => {
  const { data } = await api.get(`/jobs/${id}`)
  return data
}