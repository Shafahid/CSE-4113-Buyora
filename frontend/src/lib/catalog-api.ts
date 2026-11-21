import { jsonBody, request } from "./api-client";
import type { ApiSchemas } from "./api-schema";

export const catalogApi = {
  products: (status: "active" | "archived") => request<ApiSchemas["ProductResponse"][]>(`/products?status=${status}`),
  product: (id: string) => request<ApiSchemas["ProductDetail"]>(`/products/${id}`),
  createProduct: (data: ApiSchemas["ProductCreate"]) => request<ApiSchemas["ProductResponse"]>("/products", { method: "POST", ...jsonBody(data) }),
  updateProduct: (id: string, data: ApiSchemas["ProductUpdate"]) => request<ApiSchemas["ProductResponse"]>(`/products/${id}`, { method: "PATCH", ...jsonBody(data) }),
  duplicateProduct: (id: string) => request<ApiSchemas["ProductResponse"]>(`/products/${id}/duplicate`, { method: "POST" }),
  deleteProduct: (id: string) => request<void>(`/products/${id}`, { method: "DELETE" }),
  uploadImage: (id: string, file: File) => {
    const body = new FormData(); body.append("file", file);
    return request<ApiSchemas["ImageCreated"]>(`/products/${id}/images`, { method: "POST", body });
  },
  deleteImage: (id: string, imageId: string) => request<void>(`/products/${id}/images/${imageId}`, { method: "DELETE" }),
  posts: (productId: string) => request<ApiSchemas["PostListItem"][]>(`/products/${productId}/posts`),
  post: (id: string) => request<ApiSchemas["PostDetail"]>(`/posts/${id}`),
  versions: (id: string) => request<ApiSchemas["VersionResponse"][]>(`/posts/${id}/versions`),
  createPost: (productId: string, data: ApiSchemas["VersionInput"]) => request<ApiSchemas["PostDetail"]>(`/products/${productId}/posts`, { method: "POST", ...jsonBody(data) }),
  createVersion: (id: string, data: ApiSchemas["VersionInput"]) => request<ApiSchemas["VersionResponse"]>(`/posts/${id}/versions`, { method: "POST", ...jsonBody(data) }),
  deletePost: (id: string) => request<void>(`/posts/${id}`, { method: "DELETE" }),
};
