import axios, { AxiosInstance } from 'axios';

export interface TelegramCredentialsRequest {
  api_id?: number;
  api_hash?: string;
  session_string?: string;
}

export interface MessageButton {
  text: string;
  callback_data?: string | null;
}

export type ResponseType =
  | 'message'
  | 'edited_message'
  | 'callback_answer'
  | 'popup';

export interface BotResponse {
  response_type: ResponseType;
  message_id?: number;
  message_text?: string;
  reply_markup?: MessageButton[][] | null;
  reply_keyboard?: boolean | null;
  callback_answer_text?: string;
  callback_answer_alert?: boolean;
  popup_message?: string;
}

export interface SendMessageRequest {
  bot_username: string;
  message_text: string;
  timeout_sec?: number;
}

export interface PressButtonRequest {
  bot_username: string;
  button_text?: string;
  callback_data?: string;
  timeout_sec?: number;
}

export interface GetMessagesResponse {
  messages: BotResponse[];
}

function buildHeaders(creds?: TelegramCredentialsRequest): Record<string, string> {
  const headers: Record<string, string> = {};
  if (!creds) return headers;
  if (creds.api_id !== undefined) headers['X-Telegram-Api-Id'] = String(creds.api_id);
  if (creds.api_hash !== undefined) headers['X-Telegram-Api-Hash'] = creds.api_hash;
  if (creds.session_string !== undefined) headers['X-Telegram-Session-String'] = creds.session_string;
  return headers;
}

export class TeletestApiClient {
  constructor(private baseUrl: string, private http: AxiosInstance = axios.create()) {}

  async sendMessage(req: SendMessageRequest, creds?: TelegramCredentialsRequest): Promise<BotResponse[]> {
    const resp = await this.http.post<BotResponse[]>(`${this.baseUrl}/send-message`, req, {
      headers: buildHeaders(creds)
    });
    return resp.data;
  }

  async pressButton(req: PressButtonRequest, creds?: TelegramCredentialsRequest): Promise<BotResponse[]> {
    const resp = await this.http.post<BotResponse[]>(`${this.baseUrl}/press-button`, req, {
      headers: buildHeaders(creds)
    });
    return resp.data;
  }

  async getMessages(bot_username: string, limit = 5, creds?: TelegramCredentialsRequest): Promise<GetMessagesResponse> {
    const resp = await this.http.get<GetMessagesResponse>(`${this.baseUrl}/get-messages`, {
      headers: buildHeaders(creds),
      params: { bot_username, limit }
    });
    return resp.data;
  }
}

export default TeletestApiClient;
