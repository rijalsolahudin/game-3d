/** Sumber tunggal kode error API. Didokumentasikan di server/docs/error-codes.md. */
export const ERROR_CODES = {
  VALIDATION_ERROR: 'VALIDATION_ERROR',
  INVALID_JSON: 'INVALID_JSON',
  UNSUPPORTED_MEDIA_TYPE: 'UNSUPPORTED_MEDIA_TYPE',
  PAYLOAD_TOO_LARGE: 'PAYLOAD_TOO_LARGE',
  BAD_REQUEST: 'BAD_REQUEST',
  CLIENT_ERROR: 'CLIENT_ERROR',
  METHOD_NOT_ALLOWED: 'METHOD_NOT_ALLOWED',
  REQUEST_TIMEOUT: 'REQUEST_TIMEOUT',
  UNAUTHORIZED: 'UNAUTHORIZED',
  FORBIDDEN: 'FORBIDDEN',
  NOT_FOUND: 'NOT_FOUND',
  CONFLICT: 'CONFLICT',
  RATE_LIMITED: 'RATE_LIMITED',
  INTERNAL_ERROR: 'INTERNAL_ERROR',
} as const;

export type ErrorCode = (typeof ERROR_CODES)[keyof typeof ERROR_CODES];

export interface ErrorDetail {
  path: string;
  message: string;
}

/** Error aplikasi yang aman ditampilkan ke client (code + message dikontrol kita). */
export class AppError extends Error {
  constructor(
    readonly statusCode: number,
    readonly code: ErrorCode,
    message: string,
    readonly details?: ErrorDetail[],
  ) {
    super(message);
    this.name = 'AppError';
  }
}

interface MappedError {
  status: number;
  code: ErrorCode;
  message: string;
}

/** Pemetaan kode error internal Fastify (FST_ERR_*) ke kode milik kita. */
export const FASTIFY_ERROR_MAP: Record<string, MappedError> = {
  FST_ERR_CTP_INVALID_JSON_BODY: {
    status: 400,
    code: ERROR_CODES.INVALID_JSON,
    message: 'Body JSON tidak valid',
  },
  FST_ERR_CTP_EMPTY_JSON_BODY: {
    status: 400,
    code: ERROR_CODES.INVALID_JSON,
    message: 'Body JSON tidak boleh kosong',
  },
  FST_ERR_CTP_INVALID_CONTENT_LENGTH: {
    status: 400,
    code: ERROR_CODES.BAD_REQUEST,
    message: 'Content-Length tidak sesuai dengan body',
  },
  FST_ERR_CTP_INVALID_MEDIA_TYPE: {
    status: 415,
    code: ERROR_CODES.UNSUPPORTED_MEDIA_TYPE,
    message: 'Content-Type tidak didukung',
  },
  FST_ERR_CTP_BODY_TOO_LARGE: {
    status: 413,
    code: ERROR_CODES.PAYLOAD_TOO_LARGE,
    message: 'Body request terlalu besar',
  },
};

export const GENERIC_4XX: Record<number, { code: ErrorCode; message: string }> = {
  400: { code: ERROR_CODES.BAD_REQUEST, message: 'Request tidak valid' },
  401: { code: ERROR_CODES.UNAUTHORIZED, message: 'Autentikasi diperlukan' },
  403: { code: ERROR_CODES.FORBIDDEN, message: 'Akses ditolak' },
  404: { code: ERROR_CODES.NOT_FOUND, message: 'Sumber tidak ditemukan' },
  405: { code: ERROR_CODES.METHOD_NOT_ALLOWED, message: 'Metode HTTP tidak diizinkan' },
  408: { code: ERROR_CODES.REQUEST_TIMEOUT, message: 'Request melewati batas waktu' },
  409: { code: ERROR_CODES.CONFLICT, message: 'Konflik dengan keadaan sumber saat ini' },
  429: { code: ERROR_CODES.RATE_LIMITED, message: 'Terlalu banyak request, coba lagi nanti' },
};
