import { useQueryClient } from '@tanstack/react-query';
import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { alVencerLaSesion, guardarToken, leerToken } from '../api/client.js';
import { iniciarSesion, obtenerYo } from '../api/auth.js';
import { MENSAJES } from '../utils/mensajes.js';

const SesionContext = createContext(null);

/**
 * Sesión de la persona usuaria. Al iniciar restaura la sesión con `GET /auth/me` si hay token;
 * ante cualquier 401 la cierra y deja un aviso para el login.
 */
export function SesionProvider({ children }) {
  const queryClient = useQueryClient();
  const [estado, setEstado] = useState(() => (leerToken() ? 'cargando' : 'anonimo'));
  const [usuario, setUsuario] = useState(null);
  const [aviso, setAviso] = useState(null);

  const descartar = useCallback(
    (mensaje = null) => {
      guardarToken(null);
      queryClient.clear();
      setUsuario(null);
      setAviso(mensaje);
      setEstado('anonimo');
    },
    [queryClient],
  );

  useEffect(() => {
    alVencerLaSesion(() => descartar(MENSAJES.sesionVencida));
  }, [descartar]);

  useEffect(() => {
    if (!leerToken()) return undefined;
    let activo = true;
    obtenerYo()
      .then((datos) => {
        if (!activo) return;
        setUsuario(datos);
        setEstado('autenticado');
      })
      .catch((error) => {
        if (!activo) return;
        if (error.estado === 401) descartar();
        else {
          guardarToken(null);
          setAviso(MENSAJES.sinConexion);
          setEstado('anonimo');
        }
      });
    return () => {
      activo = false;
    };
    // Solo al montar: restaura la sesión guardada.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const iniciar = useCallback(async (username, password) => {
    const respuesta = await iniciarSesion(username, password);
    guardarToken(respuesta.access_token);
    setUsuario(respuesta.usuario);
    setAviso(null);
    setEstado('autenticado');
    return respuesta.usuario;
  }, []);

  const valor = useMemo(
    () => ({
      estado,
      usuario,
      aviso,
      iniciar,
      cerrar: () => descartar(),
      tienePermiso: (permiso) => Boolean(usuario?.permisos?.includes(permiso)),
    }),
    [estado, usuario, aviso, iniciar, descartar],
  );
  return <SesionContext.Provider value={valor}>{children}</SesionContext.Provider>;
}

/** `{ estado, usuario, aviso, iniciar, cerrar, tienePermiso }` */
export function useSesion() {
  const contexto = useContext(SesionContext);
  if (!contexto) throw new Error('useSesion debe usarse dentro de SesionProvider');
  return contexto;
}
