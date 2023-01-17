import axios from "axios";
import type { ProgressResponse, Results, ResultsQuery, SearchStartRequest, SearchStartResponse } from "./Models";

export namespace Api {
    let ROOT_URL = "ROOT_URL_PLACEHOLDER";

    export async function searchStart(request: SearchStartRequest): Promise<SearchStartResponse> {
        const response = await axios({
            method: "post",
            url: `https://${ROOT_URL}/api/search`,
            data:request,
            headers: {
                'Access-Control-Allow-Origin': '*',
                Accept: 'application/json',
                credentials: 'include',
                'Content-Type': 'application/json',
            },
        })
        return response.data
    }

    export async function getProgress(queryId: string): Promise<ProgressResponse> {
        const response = await axios({
            method: "get",
            url: `https://${ROOT_URL}/api/status/${queryId}`,
            headers: {
                'Access-Control-Allow-Origin': '*',
                Accept: 'application/json',
                credentials: 'include',
                'Content-Type': 'application/json',
            },
        })
        return response.data
    }

    export async function getResults(queryId: string): Promise<Results> {
        const response = await axios({
            method: "get",
            url: `https://${ROOT_URL}/api/results/${queryId}`,
            headers: {
                'Access-Control-Allow-Origin': '*',
                Accept: 'application/json',
                credentials: 'include',
                'Content-Type': 'application/json',
            },
        })
        return response.data
    }

    export async function align(queryResults: ResultsQuery): Promise<ResultsQuery> {
        const response = await axios({
            method: "post",
            url: `https://${ROOT_URL}/api/align/`,
            headers: {
                'Access-Control-Allow-Origin': '*',
                Accept: 'application/json',
                credentials: 'include',
                'Content-Type': 'application/json',
            },
            data: queryResults,
        })
        return response.data
    }

    interface AlignResults {
        progress ?: string;
        result ?: ResultsQuery;
    }

    export async function alignSocket(queryResults: ResultsQuery, onProgress: (string) => void, onResult: (ResultsQuery) => void) {
        const socket = new WebSocket(`wss://${ROOT_URL}/ws/api/align`);
        socket.addEventListener('open', (e) => {
            socket.send(JSON.stringify(queryResults));
            socket.addEventListener('message', function (event) {
                let r: AlignResults = JSON.parse(event.data);
                if (r.progress !== undefined) {
                    onProgress(r.progress)
                } else {
                    onResult(r.result)
                    socket.close()
                }
            });
        })
    }

    export function resultsArchiveUrl(queryId: string): string {
        return `https://${ROOT_URL}/api/results_archive/${queryId}`
    }

}