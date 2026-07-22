export type Filters = {
  page?: number;
  page_size?: number;
  sort_by?: string;
  date?: string;
  keyword?: string;
  min_score?: number;
};

export type LanguageDatum = {
  language: string;
  count: number;
};
