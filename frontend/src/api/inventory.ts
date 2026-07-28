const API_URL = "http://localhost:8000";

export interface Skin {
    id_: number;
    skin_name: string;
    float_val: number;
    purchase_price: number;
    recorded_at: string;
    expected_sale_price: number;
    profit: number;
}

export interface NewSkin {
    skin_name: string;
    float_val: number;
    purchase_price: number;
}

export interface StatusResponse {
    status: string;
}

async function getJson<T>(url: string): Promise<T> {
    const response = await fetch(url);

    if (!response.ok) {
        throw new Error(`Failed to fetch ${url}: ${response.status} ${response.statusText}`);
    }

    return (await response.json()) as T;
}

async function postJson<TRequest, TResponse>(url: string, body: TRequest): Promise<TResponse> {
    const response = await fetch(url, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify(body)
    });

    if (!response.ok) {
        throw new Error(`Failed to post to ${url}: ${response.status} ${response.statusText}`);
    }

    return (await response.json()) as TResponse;
}

async function delJson<TResponse>(url: string): Promise<TResponse> {
    const response = await fetch(url, {
        method: "DELETE",
    });

    if (!response.ok) {
        throw new Error(`Failed to send delete request to ${url}: ${response.status} ${response.statusText}`)
    }

    return (await response.json()) as TResponse;
}

export function getInventory(): Promise<Skin[]> {
    return getJson<Skin[]>(`${API_URL}/inventory`);
}

export function addSkin(newSkin: NewSkin): Promise<StatusResponse> {
    return postJson<NewSkin, StatusResponse>(`${API_URL}/inventory`, newSkin)
}

export function delSkin(id_: number): Promise<StatusResponse> {
    const url = `${API_URL}/inventory/${id_}`;
    return delJson<StatusResponse>(url)
}