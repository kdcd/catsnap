
export interface SearchStartRequest {
    database_type: string;
    search_type: string;
    query?: string;
    iso1?: string;
    iso2?: string;
    gene?: string;
}


export interface SearchStartResponse {
    query_id?: string;
    error?: string;
}

export interface ResultsItem {
    name: string;
    sequence: string;
}

export interface ResultsQuery {
    query: string
    items: ResultsItem[]
}

export interface Results {
    queryResults: ResultsQuery[];
}

export interface ProgressResponse {
    progress: number
    description: string
}