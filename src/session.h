#ifndef SESSION_H
#define SESSION_H

/// session id describing a subdirectory of the data directory
struct session_id{
	/// zero terminated public part of the session id
	char pub[12];
	/// zero terminated secret part of the session id
	char secret[32];
};

/// create and open a session. sid is filled with a random session id.
/// on error, -1 is returned and errno is set.
int session_create(struct session_id *sid);

/// open existing session.
/// on error, -1 is returned and errno is set.
int session_open(const struct session_id *sid);

#endif /*SESSION_H*/
