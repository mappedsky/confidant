import { useEffect, useRef, useState } from 'react';

interface CursorPaginatedResponse {
  next_page?: string | null;
}

interface UseAllCursorPagesOptions<TItem, TResponse extends CursorPaginatedResponse> {
  fetchPage: (page?: string) => Promise<TResponse>;
  getRows: (response: TResponse) => TItem[];
}

export function useAllCursorPages<TItem, TResponse extends CursorPaginatedResponse>({
  fetchPage,
  getRows,
}: UseAllCursorPagesOptions<TItem, TResponse>) {
  const [rows, setRows] = useState<TItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const requestIdRef = useRef(0);
  const fetchPageRef = useRef(fetchPage);
  const getRowsRef = useRef(getRows);

  useEffect(() => {
    fetchPageRef.current = fetchPage;
    getRowsRef.current = getRows;
  }, [fetchPage, getRows]);

  useEffect(() => {
    const requestId = ++requestIdRef.current;

    async function loadAllPages() {
      setLoading(true);
      setError(null);
      setRows([]);

      try {
        const collectedRows: TItem[] = [];
        let nextPage: string | undefined;

        do {
          const response = await fetchPageRef.current(nextPage);
          collectedRows.push(...getRowsRef.current(response));

          if (requestId !== requestIdRef.current) {
            return;
          }

          setRows([...collectedRows]);
          nextPage = response.next_page ?? undefined;
        } while (nextPage);
      } catch (err) {
        if (requestId !== requestIdRef.current) {
          return;
        }
        setRows([]);
        setError((err as Error).message);
      } finally {
        if (requestId === requestIdRef.current) {
          setLoading(false);
        }
      }
    }

    loadAllPages();
  }, []);

  return {
    rows,
    loading,
    error,
  };
}
