import { useMutation, useQuery, type UseMutationOptions, type UseQueryOptions, type QueryKey } from "@tanstack/react-query";

import { useAuth } from "../contexts/AuthContext";
import { useMode } from "../contexts/ModeContext";
import { prismFetch, PrismApiError } from "../lib/api-client";
import type { PrismResponse } from "../lib/types";

type QueryProps<T> = {
  queryKey: QueryKey;
  path: string;
  enabled?: boolean;
  options?: Omit<UseQueryOptions<PrismResponse<T>, PrismApiError, PrismResponse<T>, QueryKey>, "queryKey" | "queryFn">;
};

export function usePrismQuery<T>({ queryKey, path, enabled = true, options }: QueryProps<T>) {
  const { authorization } = useAuth();
  const { mode } = useMode();

  return useQuery<PrismResponse<T>, PrismApiError>({
    queryKey,
    enabled: enabled && Boolean(authorization),
    queryFn: ({ signal }) => prismFetch<T>(path, { authorization, mode, signal }),
    ...options,
  });
}

type MutationFn<TInput, TOutput> = (input: TInput) => Promise<PrismResponse<TOutput>>;

type MutationProps<TInput, TOutput> = {
  path: string;
  method?: "POST" | "PUT" | "PATCH" | "DELETE";
  options?: UseMutationOptions<PrismResponse<TOutput>, PrismApiError, TInput>;
};

export function usePrismMutation<TInput, TOutput>({ path, method = "POST", options }: MutationProps<TInput, TOutput>) {
  const { authorization } = useAuth();
  const { mode } = useMode();

  const mutationFn: MutationFn<TInput, TOutput> = async (input) => {
    return prismFetch<TOutput>(path, { method, body: input, authorization, mode });
  };

  return useMutation<PrismResponse<TOutput>, PrismApiError, TInput>({
    mutationFn,
    ...options,
  });
}
